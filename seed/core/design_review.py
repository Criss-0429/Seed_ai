"""S10.3 Design Reviewer: review indipendente contro le direttive SEED.

Regole (doc `13`):
- il reviewer e' READ-ONLY: non modifica artefatti, non approva, non promuove,
  non cambia direttive. Produce solo evidenza;
- una review e' evidenza fallibile, non sostituisce test, permission contract,
  privacy gate, lineage, rollback o owner gate;
- Ollama Cloud non supporta structured outputs: l'output del reviewer e'
  validato LOCALMENTE contro lo schema. Parsing fallito o campi mancanti/
  incoerenti producono `inconclusive`, MAI un falso `pass`.

L'esito viene registrato come evidenza nel lineage (`design_review_recorded`) e
salvato per intero sotto `lab/design_reviews/<candidate_id>.json`. Audit e
lineage restano aggregati: verdict, pack version, modello, conteggio violazioni.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .directive_pack import DIRECTIVE_IDS, DesignDirectivePack
from .llm import parse_json_object
from .ui_governance import UI_DIRECTIVE_IDS, evaluate_ui_mutation

log = logging.getLogger("seed.review")

REVIEW_VERSION = "seed.design-review.v1"
ROLE = "design_reviewer"
_VERDICTS = {"pass", "fail", "inconclusive"}
_SEVERITIES = {"blocking", "high", "medium", "low"}

_REVIEWER_SYSTEM = (
    "Sei il design reviewer indipendente di SEED. Ricevi un Design Directive Pack "
    "(direttive canoniche + artefatti di una candidate) e devi confrontarli.\n"
    "Sei READ-ONLY: non approvi, non promuovi, non modifichi nulla. La tua review "
    "e' solo evidenza per l'owner.\n"
    "Rispondi con UN SOLO oggetto JSON, senza testo fuori dal JSON, con schema:\n"
    '{"verdict":"pass|fail|inconclusive","violations":[{"directive_id":"...",'
    '"severity":"blocking|high|medium|low","evidence_ref":"diff:path:line",'
    '"reason":"breve"}],"missing_evidence":[],"recommended_checks":[]}\n'
    "Usa solo i directive_id presenti nel pack. Se manca evidenza per decidere, "
    "verdict='inconclusive'. Non inventare violazioni; non dichiarare 'pass' se "
    "esiste una violazione blocking."
)


@dataclass
class ReviewViolation:
    directive_id: str
    severity: str
    evidence_ref: str = ""
    reason: str = ""


@dataclass
class ReviewResult:
    review_version: str
    candidate_id: str
    directive_pack_version: str
    verdict: str
    model: str
    violations: list[ReviewViolation] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    recommended_checks: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> int:
        return sum(1 for v in self.violations if v.severity == "blocking")

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _inconclusive(candidate_id: str, pack_version: str, model: str,
                  reason: str) -> ReviewResult:
    return ReviewResult(
        review_version=REVIEW_VERSION,
        candidate_id=candidate_id,
        directive_pack_version=pack_version,
        verdict="inconclusive",
        model=model,
        missing_evidence=[reason],
    )


class DesignReviewer:
    def __init__(self, lineage=None, reviews_root: str | Path | None = None,
                 audit: Callable[[str, dict], None] | None = None,
                 real_enabled: bool = False):
        self._lineage = lineage
        self._reviews_root = Path(reviews_root) if reviews_root else None
        self._audit = audit
        # S10.5 owner gate: di default il reviewer gira solo in SHADOW su candidate
        # sintetiche. Le candidate REALI richiedono abilitazione esplicita owner.
        self._real_enabled = real_enabled

    # ------------------------------------------------------------------
    def review(self, pack: DesignDirectivePack, models, *,
               candidate_id: str, shadow: bool = True) -> ReviewResult:
        pack_version = pack.directive_pack_version
        model_name = models.model_for(ROLE) or "(unconfigured)"
        deterministic = self._ui_gate(pack, candidate_id, model_name)
        if deterministic is not None:
            return self._finish(deterministic, shadow=shadow)
        # S10.5: review su candidate reale bloccata finche' l'owner non apre il gate.
        if not shadow and not self._real_enabled:
            return self._finish(_inconclusive(
                candidate_id, pack_version, model_name,
                "owner gate richiesto: review su candidate reali disabilitata"),
                shadow=shadow)
        bound = models.bind(ROLE)
        if not bound.configured:
            return self._finish(_inconclusive(
                candidate_id, pack_version, model_name,
                "design_reviewer non configurato: nessun modello/credenziale"),
                shadow=shadow)

        messages = [
            {"role": "system", "content": _REVIEWER_SYSTEM},
            {"role": "user", "content": json.dumps(pack.to_dict(), ensure_ascii=False)},
        ]
        try:
            resp = bound.chat(messages, redacted=True, temperature=0.0,
                              response_json=True)
        except Exception as exc:                       # provider/fallback falliti
            log.warning("design review fallita: %s", exc)
            return self._finish(_inconclusive(
                candidate_id, pack_version, model_name,
                "errore provider o reviewer indisponibile"), shadow=shadow)

        return self._finish(self._parse(
            resp.text, candidate_id, pack_version, model_name,
            allow_ui=pack.ui_directives is not None), shadow=shadow)

    # ------------------------------------------------------------------
    def _parse(self, text: str, candidate_id: str, pack_version: str,
               model: str, *, allow_ui: bool = False) -> ReviewResult:
        """Validazione locale dello schema (no structured outputs cloud).
        Qualsiasi incoerenza -> inconclusive, mai un falso pass."""
        try:
            data = parse_json_object(text)
        except Exception:
            return _inconclusive(candidate_id, pack_version, model,
                                 "output reviewer non e' un oggetto JSON")
        verdict = data.get("verdict")
        if verdict not in _VERDICTS:
            return _inconclusive(candidate_id, pack_version, model,
                                 "verdict mancante o invalido")

        violations: list[ReviewViolation] = []
        raw = data.get("violations") or []
        if not isinstance(raw, list):
            return _inconclusive(candidate_id, pack_version, model,
                                 "campo violations malformato")
        for item in raw:
            if not isinstance(item, dict):
                return _inconclusive(candidate_id, pack_version, model,
                                     "violation malformata")
            did = item.get("directive_id")
            sev = item.get("severity")
            allowed_ids = DIRECTIVE_IDS | (UI_DIRECTIVE_IDS if allow_ui else frozenset())
            if did not in allowed_ids or sev not in _SEVERITIES:
                return _inconclusive(candidate_id, pack_version, model,
                                     "violation con directive_id/severity non validi")
            violations.append(ReviewViolation(
                directive_id=did, severity=sev,
                evidence_ref=str(item.get("evidence_ref", ""))[:200],
                reason=str(item.get("reason", ""))[:500]))

        # Coerenza: un pass non puo' convivere con una violazione blocking; un
        # fail deve dichiarare almeno una violazione.
        if verdict == "pass" and any(v.severity == "blocking" for v in violations):
            return _inconclusive(candidate_id, pack_version, model,
                                 "pass incoerente con violazione blocking")
        if verdict == "fail" and not violations:
            return _inconclusive(candidate_id, pack_version, model,
                                 "fail senza violazioni dichiarate")

        return ReviewResult(
            review_version=REVIEW_VERSION,
            candidate_id=candidate_id,
            directive_pack_version=pack_version,
            verdict=verdict,
            model=model,
            violations=violations,
            missing_evidence=[str(x)[:200] for x in (data.get("missing_evidence") or [])][:20],
            recommended_checks=[str(x)[:200] for x in (data.get("recommended_checks") or [])][:20],
        )

    def _ui_gate(self, pack: DesignDirectivePack, candidate_id: str,
                 model: str) -> ReviewResult | None:
        """Gate deterministico prima del reviewer fallibile.

        Le mutation UI dichiarano livelli violati/evidenze nel candidate pack.
        P0/P1 e P4 senza evidenza P2/P3 vengono bloccate senza chiamare un LLM.
        """
        if pack.ui_directives is None:
            return None
        violated = tuple(pack.candidate.get("ui_violated_precedence", ()) or ())
        evidence = tuple(pack.candidate.get("ui_justifying_evidence", ()) or ())
        try:
            verdict = evaluate_ui_mutation(
                violated_precedence=violated, justifying_evidence=evidence)
        except ValueError as exc:
            return _inconclusive(candidate_id, pack.directive_pack_version, model,
                                 f"contratto governance UI invalido: {exc}")
        if verdict.candidable:
            return None
        ids = {
            "P0_control_safety": "ui.b_03",
            "P1_accessibility": "ui.e_02",
            "P4_best_practice": "ui.a_03",
        }
        return ReviewResult(
            review_version=REVIEW_VERSION,
            candidate_id=candidate_id,
            directive_pack_version=pack.directive_pack_version,
            verdict="fail",
            model="deterministic-ui-gate",
            violations=[
                ReviewViolation(
                    directive_id=ids[level],
                    severity="blocking",
                    evidence_ref="candidate:ui_violated_precedence",
                    reason=f"{level} violato: gate UI non derogabile",
                )
                for level in verdict.blocking
            ],
            recommended_checks=list(verdict.reasons),
        )

    # ------------------------------------------------------------------
    def _finish(self, result: ReviewResult, *, shadow: bool = True) -> ReviewResult:
        """Persistenza evidenza: file completo + lineage aggregato + audit.
        Il reviewer non scrive artefatti e non promuove: scrive solo la propria
        review come evidenza, marcata shadow/reale."""
        if self._reviews_root is not None:
            try:
                self._reviews_root.mkdir(parents=True, exist_ok=True)
                (self._reviews_root / f"{result.candidate_id}.json").write_text(
                    json.dumps({**result.to_dict(), "shadow": shadow},
                               ensure_ascii=False, indent=2),
                    encoding="utf-8")
            except OSError as exc:
                log.warning("review non salvata su disco: %s", exc)
        if self._lineage is not None:
            try:
                self._lineage.append_event(
                    "design_review_recorded",
                    mutation_id=result.candidate_id,
                    payload={
                        "verdict": result.verdict,
                        "directive_pack_version": result.directive_pack_version,
                        "model": result.model,
                        "violations": len(result.violations),
                        "blocking": result.blocking,
                        "shadow": shadow,
                    })
            except Exception as exc:                   # lineage non deve mai rompere la chat
                log.warning("evidenza review non registrata nel lineage: %s", exc)
        if self._audit is not None:
            self._audit("design_review", {
                "verdict": result.verdict,
                "model": result.model,
                "violations": len(result.violations),
                "blocking": result.blocking,
                "shadow": shadow,
            })
        return result
