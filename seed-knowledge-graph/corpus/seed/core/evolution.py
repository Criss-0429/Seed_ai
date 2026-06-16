"""Evolution engine: reflection pass notturno.

Non training: SELEZIONE. L'LLM frontier propone n mutazioni candidate,
un secondo giro legacy seleziona un sottoinsieme. S2 registra ogni proposta
selezionata come MutationCandidate nel lineage e NON la applica. L'attivazione
richiedera' descendant, evaluator e promotion gate nelle feature successive.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import date, datetime
from pathlib import Path

from . import forbidden
from .capabilities import validate_manifest
from .descendant import DescendantBuildError, DescendantBuilder
from .directive_pack import build_directive_pack
from .evaluator import EvaluationError, EvaluatorHarness
from .lineage import LineageError, LineageStore, MutationCandidate
from .llm import parse_json_object
from .promotion import PromotionAuthority, PromotionError

log = logging.getLogger("seed.evolution")

MUTATION_TYPES = ("trait_change", "new_capability", "prune_capability",
                  "policy_change", "ui_change", "persona_change")

_PROPOSER_PROMPT = """Sei l'evolution engine di SEED, un'app desktop che si adatta al suo utente.
Riceverai il diario redatto della giornata di un utente (eventi, uso capability, feedback).
Proponi da 3 a 7 mutazioni candidate in JSON. Ogni mutazione:
{"type": una tra %s,
 "target": "id tratto/capability/policy/widget",
 "diff": oggetto col cambiamento proposto,
 "reason": "perche' PER QUESTO utente, citando le evidenze del diario",
 "expected_signal": "predizione osservabile e falsificabile entro 3 giorni",
 "risk_class": "safe|read_safe|read_sensitive|execute|network|write",
 "permissions_delta": []}
Contratti diff:
- trait_change: target e' un path esistente, diff e' {"value": valore};
- policy_change: diff contiene almeno trigger e action;
- ui_change: diff cambia solo chiavi esistenti di theme o widgets;
- ui_change: cita `design_directives` pertinenti (A-01..E-05) e dichiara
  `ui_violated_precedence` + `ui_justifying_evidence`; omissioni non autorizzano
  deroghe a P0 controllo/sicurezza o P1 accessibilita';
- persona_change: diff cambia solo chiavi esistenti di persona;
- new_capability: manifest include capability_id, description, input_schema,
  risk_class e origin.
Per new_capability includi in diff: {"manifest": {...}, "code": "python con I/O JSON stdin/stdout"}.
Il codice puo' importare solo: json, re, math, datetime, pathlib, csv, collections,
itertools, textwrap, statistics, html, base64. Niente subprocess/eval/ctypes/rete
(salvo needs_network dichiarato).
PERSONA: proponi compatibilita contestuale, non una copia dell'utente. Conserva
capacita di dissenso, continuita e un registro distinto; niente mirroring o
compiacenza. Ogni variazione deve essere giustificata dal diario.
Rispondi SOLO con {"mutations": [...]}.""" % str(MUTATION_TYPES)

_SELECTOR_PROMPT = """Sei il selettore dell'evolution engine. Riceverai mutazioni candidate
e il contesto (tratti attuali, cooldown, soppressioni, esiti delle predizioni passate).
Scegli AL MASSIMO %d mutazioni applicando:
score = evidence_strength * expected_value * reversibility - novelty_cost - risk_penalty
Vincoli: mai due dello stesso tipo; rispetta i cooldown; mai riproporre mutazioni soppresse;
se nessuna merita, scegli zero (e' un esito valido).
Rispondi SOLO con {"selected": [indici], "reasoning": "breve"}."""


class EvolutionEngine:
    def __init__(self, config, memory, privacy_gate, llm, registry):
        self._cfg = config.evolution
        self._llm_cfg = config.llm
        self._memory = memory
        self._gate = privacy_gate
        self._llm = llm
        self._registry = registry
        self.state_dir = forbidden.seed_data_dir() / "state"
        self.versions_dir = forbidden.seed_data_dir() / "versions"
        self.lineage = LineageStore(forbidden.seed_data_dir() / "lineage")
        self.descendants = DescendantBuilder(
            forbidden.seed_data_dir() / "lab" / "descendants",
            self.versions_dir,
        )
        self.evaluator = EvaluatorHarness(
            self.lineage,
            self.descendants,
            forbidden.seed_data_dir() / "lab" / "evaluator_runs",
            forbidden.seed_data_dir() / "lab" / "replay_fixtures",
        )
        self.promotion = PromotionAuthority(
            self.lineage,
            self.descendants,
            self.evaluator,
            self.state_dir,
            forbidden.seed_data_dir() / "capabilities",
            self.versions_dir,
            forbidden.seed_data_dir() / "active",
            forbidden.seed_data_dir() / "lab" / "canary_leases",
            on_runtime_changed=self._registry.reload,
        )
        self._design_reviewer = None
        self._design_models = None
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def set_design_reviewer(self, reviewer, models) -> None:
        """Collega il reviewer read-only senza conferirgli promotion authority."""
        self._design_reviewer = reviewer
        self._design_models = models

    # ------------------------------------------------------------------
    # file di stato (strato 2/4)
    # ------------------------------------------------------------------
    def _load_json(self, name: str, default: dict, context_id: str = "") -> dict:
        p = self.promotion.state_dir_for_context(context_id) / name
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                log.error("%s corrotto, uso default", name)
        return default

    def _save_json(self, name: str, data: dict) -> None:
        (self.state_dir / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def user_model(self, context_id: str = "") -> dict:
        return self._load_json("user_model.json", _DEFAULT_USER_MODEL(), context_id)

    def policy(self, context_id: str = "") -> dict:
        return self._load_json(
            "policy.json", {"rules": [], "suppressions": []}, context_id)

    def ui_manifest(self, context_id: str = "") -> dict:
        return self._load_json("ui_manifest.json", _DEFAULT_UI_MANIFEST(), context_id)

    def pending_digest(self) -> dict:
        return self._load_json(
            "digest.json", {"date": None, "applied": [], "proposed": [], "notes": []})

    # ------------------------------------------------------------------
    # reflection pass
    # ------------------------------------------------------------------
    def already_ran_today(self) -> bool:
        marker = self._load_json("last_reflection.json", {})
        return marker.get("date") == date.today().isoformat()

    def run_reflection(self) -> dict:
        """Collect -> redact -> propose -> select -> lineage -> validation-only.

        S2 invariant: this method never applies a mutation to the active runtime.
        """
        if not self._cfg.enabled:
            digest = {"date": date.today().isoformat(), "applied": [], "proposed": [],
                      "notes": ["evolution disabilitata (istanza baseline)"]}
            self._save_json("digest.json", digest)
            self._save_json("last_reflection.json", {"date": date.today().isoformat()})
            return digest

        digest: dict = {
            "date": date.today().isoformat(), "applied": [], "proposed": [], "notes": []}
        try:
            diary = self._collect_diary()
            proposals = self._propose(diary)
            selected = self._select(proposals)
            if selected:
                parent = self._snapshot()
                for mutation in selected:
                    self._register_legacy_candidate(mutation, parent.name, digest)
            self._check_predictions(digest)
            self._prune_pass(digest)
        except Exception as exc:
            log.exception("reflection fallita")
            digest["notes"].append({"error": str(exc)})
        self._save_json("digest.json", digest)
        self._save_json("last_reflection.json", {"date": date.today().isoformat()})
        self._memory.add_event("reflection", {
            "applied": len(digest["applied"]),
            "proposed": len(digest["proposed"]),
        })
        return digest

    def _register_legacy_candidate(
        self,
        mutation: dict,
        parent_version: str,
        digest: dict,
    ) -> None:
        """Convert a selected legacy proposal into a governed lineage record."""
        try:
            candidate = _candidate_from_legacy(mutation, parent_version)
            self.lineage.record_candidate(candidate, proposal=mutation)
            errors = self._validate_legacy_proposal(mutation)
            if errors:
                self.lineage.record_evaluation(
                    candidate.mutation_id,
                    "legacy-schema-validator",
                    "fail",
                    metrics={"schema_valid": False, "errors": errors},
                    notes="Validation-only S2 gate; no active runtime change.",
                )
                rejected = self.lineage.transition(
                    candidate, "rejected", reason="; ".join(errors))
                digest["notes"].append({
                    "mutation_id": rejected.mutation_id,
                    "mutation": _strip_code(mutation),
                    "status": rejected.status,
                    "errors": errors,
                })
                return
            self.lineage.record_evaluation(
                candidate.mutation_id,
                "legacy-schema-validator",
                "inconclusive",
                metrics={"schema_valid": True},
                notes="Schema valid only; descendant evaluation still required.",
            )
            artifact_path, manifest = self.descendants.build(candidate, mutation)
            artifact_ref = artifact_path.relative_to(forbidden.seed_data_dir()).as_posix()
            self.lineage.record_descendant(
                candidate.mutation_id,
                artifact_ref=artifact_ref,
                content_hash=manifest.content_hash,
                files=manifest.files,
            )
            candidate = self.lineage.transition(
                candidate, "built", reason="S3 isolated descendant materialized")
            report = self.evaluator.evaluate(candidate, mutation)
            design_review = self._review_ui_candidate(candidate, mutation, report)
            if report.outcome == "pass":
                if design_review is not None and design_review.model == "deterministic-ui-gate" \
                        and design_review.verdict == "fail":
                    recorded = self.lineage.candidate(candidate.mutation_id)
                    if recorded is None:
                        raise LineageError("candidate UI non trovata dopo evaluation")
                    candidate = self.lineage.transition(
                        recorded, "rejected",
                        reason="UI deterministic governance gate failed")
                else:
                    candidate = self.promotion.start_shadow(candidate)
            status = self.lineage.current_status(candidate.mutation_id) or "unknown"
            digest["proposed"].append({
                "mutation_id": candidate.mutation_id,
                "parent_version": parent_version,
                "mutation": _strip_code(mutation),
                "status": status,
                "artifact_ref": artifact_ref,
                "content_hash": manifest.content_hash,
                "evaluation": {
                    "outcome": report.outcome,
                    "report_hash": report.report_hash,
                    "descendant_executed": report.descendant_executed,
                    "provider_called": report.provider_called,
                },
                "design_review": (
                    {
                        "verdict": design_review.verdict,
                        "blocking": design_review.blocking,
                        "model": design_review.model,
                    }
                    if design_review is not None else None
                ),
                "note": (
                    "descendant costruito e valutato; shadow aperto senza effetti"
                    if status == "shadow"
                    else "descendant costruito e valutato; non eseguito o attivato"
                ),
            })
        except (DescendantBuildError, EvaluationError, PromotionError, LineageError) as exc:
            current = locals().get("candidate")
            evaluation_failed = isinstance(exc, EvaluationError)
            exposure_failed = isinstance(exc, PromotionError)
            failure_status = (
                "evaluation_failed" if evaluation_failed
                else "exposure_failed" if exposure_failed
                else "build_failed"
            )
            evaluator_id = (
                EvaluatorHarness.EVALUATOR_ID if evaluation_failed
                else PromotionAuthority.AUTHORITY_ID if exposure_failed
                else "descendant-builder"
            )
            if isinstance(current, MutationCandidate):
                try:
                    self.lineage.record_evaluation(
                        current.mutation_id,
                        evaluator_id,
                        "fail",
                        metrics={
                            "built": not isinstance(exc, DescendantBuildError),
                            "evaluation_error": evaluation_failed,
                            "exposure_error": exposure_failed,
                        },
                        notes=str(exc),
                    )
                    recorded = self.lineage.candidate(current.mutation_id)
                    if recorded is not None and recorded.status in {
                        "proposed", "built", "validating",
                    }:
                        current = self.lineage.transition(
                            recorded, "rejected", reason=f"{failure_status}: {exc}")
                except LineageError:
                    pass
            digest["notes"].append({
                "mutation_id": getattr(current, "mutation_id", ""),
                "mutation": _strip_code(mutation),
                "status": failure_status,
                "error": str(exc),
            })

    def _review_ui_candidate(self, candidate: MutationCandidate, mutation: dict,
                             report) -> object | None:
        """Registra evidenza design sulle candidate UI reali.

        Il reviewer LLM resta evidenza. Solo il gate deterministico P0/P1/P4
        puo' impedire l'apertura dello shadow.
        """
        if mutation.get("type") != "ui_change":
            return None
        if self._design_reviewer is None or self._design_models is None:
            return None
        artifacts = {
            "manifest": {
                "mutation_id": candidate.mutation_id,
                "scope": "ui_change",
                "target": mutation.get("target", ""),
            },
            "permission_delta": mutation.get("permissions_delta", []),
            "diff": mutation.get("diff", {}),
            "design_directives": mutation.get("design_directives", []),
            "ui_violated_precedence": mutation.get("ui_violated_precedence", []),
            "ui_justifying_evidence": mutation.get("ui_justifying_evidence", []),
            "test_report": {"outcome": report.outcome,
                            "report_hash": report.report_hash},
            "rollback_plan": candidate.rollback_plan,
        }
        pack = build_directive_pack(
            feature="UI mutation", scope="ui_change", candidate=artifacts)
        return self._design_reviewer.review(
            pack, self._design_models, candidate_id=candidate.mutation_id,
            shadow=False)

    def _validate_legacy_proposal(self, mutation: dict) -> list[str]:
        """Validation-only compatibility gate. Never mutates active state."""
        errors: list[str] = []
        mtype = mutation.get("type")
        target = mutation.get("target")
        diff = mutation.get("diff")
        if mtype not in MUTATION_TYPES:
            errors.append(f"tipo sconosciuto: {mtype}")
        if not isinstance(target, str) or not target.strip():
            errors.append("target mancante")
        if not isinstance(diff, dict):
            errors.append("diff deve essere un oggetto")
        if not isinstance(mutation.get("reason"), str) or not mutation["reason"].strip():
            errors.append("reason mancante")
        expected = mutation.get("expected_signal")
        if not isinstance(expected, str) or not expected.strip():
            errors.append("expected_signal mancante")
        if mtype == "new_capability" and isinstance(diff, dict):
            manifest = dict(diff.get("manifest") or {})
            manifest.setdefault("origin", "generated")
            errors.extend(f"manifest invalido: {error}" for error in validate_manifest(manifest))
            if not isinstance(diff.get("code"), str) or not diff["code"].strip():
                errors.append("codice capability mancante")
        return errors

    # ------------------------------------------------------------------
    def _collect_diary(self) -> str:
        since = time.time() - 86400
        episodes = self._memory.episodes_since(since)
        usage: dict[str, float] = {}
        for ep in episodes:
            if ep["source"] == "watcher":
                cat = ep["payload"].get("category", "altro")
                usage[cat] = usage.get(cat, 0) + ep["payload"].get("duration_s", 0)
        chats = [
            ep["payload"]
            for ep in episodes
            if ep["source"] == "chat" and ep.get("category") != "onboarding"
        ][-30:]
        diary = {
            "usage_hours_by_category": {k: round(v / 3600, 2) for k, v in usage.items()},
            "chat_excerpts": chats,
            "capability_stats": self._memory.capability_stats(),
            "events": [e for e in self._memory.events_since(since)
                       if e["kind"] in ("permission", "rollback", "survey")],
            "preferences": self._memory.preferences(),
            "current_traits": self.user_model(),
        }
        text = json.dumps(diary, ensure_ascii=False)
        return self._gate.redact(text, purpose="llm").text  # ridondante ma fail-safe

    def _propose(self, diary_redacted: str) -> list[dict]:
        resp = self._llm.chat(
            [{"role": "system", "content": _PROPOSER_PROMPT},
             {"role": "user", "content": diary_redacted}],
            redacted=True, temperature=0.8, response_json=True)
        try:
            return parse_json_object(resp.text).get("mutations", [])
        except json.JSONDecodeError:
            log.error("proposer: JSON invalido")
            return []

    def _select(self, proposals: list[dict]) -> list[dict]:
        if not proposals:
            return []
        context = {
            "candidates": [_strip_code(p) for p in proposals],
            "cooldowns": self._load_json("cooldowns.json", {}),
            "suppressions": self.policy().get("suppressions", []),
            "past_predictions": self._load_json("predictions.json", {"open": []}),
        }
        resp = self._llm.chat(
            [{"role": "system", "content": _SELECTOR_PROMPT % self._cfg.max_mutations_per_night},
             {"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
            redacted=True, temperature=0.2, response_json=True)
        try:
            idx = parse_json_object(resp.text).get("selected", [])
        except json.JSONDecodeError:
            return []
        chosen = [proposals[i] for i in idx if 0 <= i < len(proposals)]
        chosen = chosen[: self._cfg.max_mutations_per_night]
        seen_types: set[str] = set()
        final = []
        for m in chosen:
            if m.get("type") in seen_types:
                continue
            seen_types.add(m.get("type", ""))
            final.append(m)
        return final

    # ------------------------------------------------------------------
    def _validate_and_apply(self, mutation: dict) -> tuple[bool, str]:
        mtype = mutation.get("type")
        if mtype not in MUTATION_TYPES:
            return False, f"tipo sconosciuto: {mtype}"
        diff = mutation.get("diff") or {}
        target = str(mutation.get("target", ""))

        if mtype == "trait_change":
            cooldowns = self._load_json("cooldowns.json", {})
            last = cooldowns.get(target, 0)
            if time.time() - last < self._cfg.trait_cooldown_days * 86400:
                return False, f"cooldown attivo su {target}"
            model = self.user_model()
            if not _apply_trait_diff(model, target, diff):
                return False, f"tratto inesistente: {target}"
            model["version"] = model.get("version", 0) + 1
            model["regenerated_at"] = datetime.now().isoformat(timespec="seconds")
            self._save_json("user_model.json", model)
            cooldowns[target] = time.time()
            self._save_json("cooldowns.json", cooldowns)

        elif mtype == "new_capability":
            manifest = diff.get("manifest") or {}
            code = diff.get("code") or ""
            manifest.setdefault("origin", "generated")
            manifest.setdefault("reason", mutation.get("reason", ""))
            errors = validate_manifest(manifest)
            if errors:
                return False, f"manifest invalido: {errors}"
            ok, problems = self._registry.register_generated(manifest, code)
            if not ok:
                return False, f"forge respinto: {problems}"

        elif mtype == "prune_capability":
            if not self._registry.prune(target):
                self._registry.set_state(target, "dormant")

        elif mtype == "policy_change":
            policy = self.policy()
            rule = {**diff, "reason": mutation.get("reason", ""), "added": time.time()}
            policy.setdefault("rules", []).append(rule)
            self._save_json("policy.json", policy)

        elif mtype in ("ui_change", "persona_change"):
            ui = self.ui_manifest()
            section = "persona" if mtype == "persona_change" else "theme"
            for k, v in diff.items():
                if k in ui.get(section, {}):
                    ui[section][k] = v
                elif mtype == "ui_change" and k == "widgets":
                    ui["widgets"] = v
            ui["version"] = ui.get("version", 0) + 1
            self._save_json("ui_manifest.json", ui)

        preds = self._load_json("predictions.json", {"open": []})
        preds["open"].append({"mutation_type": mtype, "target": target,
                              "expected_signal": mutation.get("expected_signal", ""),
                              "made_at": time.time(), "check_by": time.time() + 3 * 86400})
        self._save_json("predictions.json", preds)
        return True, "applicata"

    # ------------------------------------------------------------------
    def _check_predictions(self, digest: dict) -> None:
        preds = self._load_json("predictions.json", {"open": []})
        still_open, expired = [], []
        for p in preds["open"]:
            (expired if time.time() > p.get("check_by", 0) else still_open).append(p)
        if expired:
            stats = {s["capability_id"]: s for s in self._memory.capability_stats()}
            for p in expired:
                used = stats.get(p["target"], {}).get("invocations", 0)
                verdict = "verificata" if used >= 2 else "fallita"
                digest["notes"].append({"prediction": p["expected_signal"],
                                        "target": p["target"], "verdict": verdict})
        preds["open"] = still_open
        self._save_json("predictions.json", preds)

    def _prune_pass(self, digest: dict) -> None:
        now = time.time()
        for s in self._memory.capability_stats():
            cap = self._registry.get(s["capability_id"])
            if cap is None or cap.manifest.get("origin") != "generated":
                continue
            idle_days = (now - (s["last_used"] or 0)) / 86400
            if cap.state == "active" and idle_days > self._cfg.capability_dormant_days:
                digest["notes"].append({"dormant_proposal": cap.capability_id})
            elif cap.state == "dormant" and idle_days > self._cfg.capability_prune_days:
                digest["notes"].append({"prune_proposal": cap.capability_id})

    # ------------------------------------------------------------------
    # versioning e rollback
    # ------------------------------------------------------------------
    def _snapshot(self) -> Path:
        # materializza i default mancanti: lo snapshot deve essere completo
        # perche' il rollback ripristina ESATTAMENTE questo stato
        self._save_json("user_model.json", self.user_model())
        self._save_json("policy.json", self.policy())
        self._save_json("ui_manifest.json", self.ui_manifest())
        stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S%f")
        target = self.versions_dir / stamp
        suffix = 0
        while target.exists():
            suffix += 1
            target = self.versions_dir / f"{stamp}-{suffix}"
        target.mkdir(parents=True)
        shutil.copytree(self.state_dir, target / "state", dirs_exist_ok=True)
        gen = forbidden.seed_data_dir() / "capabilities"
        if gen.exists():
            shutil.copytree(gen, target / "capabilities", dirs_exist_ok=True)
        return target

    def rollback(self, version: str, suppression_key: str = "") -> bool:
        src = self.versions_dir / version
        if not src.exists():
            return False
        if (src / "state").exists():
            shutil.rmtree(self.state_dir, ignore_errors=True)
            shutil.copytree(src / "state", self.state_dir)
        gen = forbidden.seed_data_dir() / "capabilities"
        if (src / "capabilities").exists():
            shutil.rmtree(gen, ignore_errors=True)
            shutil.copytree(src / "capabilities", gen)
        if suppression_key:
            policy = self.policy()
            policy.setdefault("suppressions", []).append(
                {"key": suppression_key, "at": time.time()})
            self._save_json("policy.json", policy)
        self._registry.reload()
        self._memory.add_event("rollback", {"version": version, "suppressed": bool(suppression_key)})
        return True


# ---------------------------------------------------------------------------
def _apply_trait_diff(model: dict, target: str, diff: dict) -> bool:
    """target tipo 'ui.density' o 'interaction.verbosity'."""
    parts = target.split(".")
    node = model
    for p in parts[:-1]:
        node = node.get(p)
        if not isinstance(node, dict):
            return False
    leaf = parts[-1]
    if leaf not in node:
        return False
    node[leaf] = diff.get("value", diff)
    return True


def _strip_code(mutation: dict) -> dict:
    """Versione senza codice per digest/selettore (il codice resta nel forge)."""
    m = dict(mutation)
    if isinstance(m.get("diff"), dict) and "code" in m["diff"]:
        m = {**m, "diff": {**m["diff"], "code": f"<{len(m['diff']['code'])} chars>"}}
    return m


def _candidate_from_legacy(mutation: dict, parent_version: str) -> MutationCandidate:
    mtype = str(mutation.get("type") or "unknown")
    target = str(mutation.get("target") or "unknown")
    reason = str(mutation.get("reason") or "[legacy proposal missing reason]")
    expected = mutation.get("expected_signal")
    expected_signals = [
        signal for signal in mutation.get("expected_signals", [])
        if isinstance(signal, dict)
        and all(isinstance(signal.get(key), str) and signal[key].strip()
                for key in ("metric", "direction", "window"))
    ] if isinstance(mutation.get("expected_signals"), list) else []
    if not expected_signals and isinstance(expected, str) and expected.strip():
        expected_signals = [{
            "metric": "legacy_expected_signal",
            "direction": "observe",
            "window": "3d",
            "description": expected,
        }]
    evidence_refs = mutation.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        evidence_refs = []
    scope_map = {
        "trait_change": "personal_state",
        "new_capability": "capability",
        "prune_capability": "capability",
        "policy_change": "policy",
        "ui_change": "ui",
        "persona_change": "personality",
    }
    permissions_delta = mutation.get("permissions_delta")
    if not isinstance(permissions_delta, list):
        permissions_delta = []
    confidence = mutation.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, float(confidence)))
    return MutationCandidate(
        parent_version=parent_version,
        reason=reason,
        evidence_refs=[str(ref) for ref in evidence_refs if str(ref).strip()],
        hypothesis=str(mutation.get("hypothesis") or expected or reason),
        target_scope=[scope_map.get(mtype, mtype), target],
        artifacts=[],
        expected_signals=expected_signals,
        evaluation_plan=["legacy_schema_validation", "descendant_replay", "canary"],
        risks=[str(mutation.get("risk_class") or "unknown")],
        permissions_delta=permissions_delta,
        rollback_plan=parent_version,
        confidence=confidence,
    )


def _DEFAULT_USER_MODEL() -> dict:
    return {
        "version": 0,
        "regenerated_at": None,
        "interaction": {"verbosity": 0.5, "formality": 0.5, "humor": 0.0,
                        "language": "it", "preferred_input": "text"},
        "ui": {"density": 0.3, "font_scale": 1.0, "palette": "mono", "motion": 0.1},
        "proactivity": {"level": 0.0, "channels": ["in_app"], "quiet_hours": ["22:00-08:00"]},
        "domains": {"observed": [], "ignored": []},
        "evidence_refs": [],
    }


def _DEFAULT_UI_MANIFEST() -> dict:
    return {
        "version": 0,
        "theme": {"palette": "mono", "font_scale": 1.0, "density": 0.3,
                  "background": "#111111", "foreground": "#e8e8e8", "accent": "#888888"},
        "persona": {"tone": "neutro, essenziale, nessuna personalita' imposta",
                    "greeting": "Ciao. Scrivimi pure."},
        "widgets": ["chat"],
    }
