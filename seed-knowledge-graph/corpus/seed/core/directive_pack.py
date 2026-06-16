"""S10.2 Design Directive Pack.

Il design reviewer (S10.3) non legge documenti a caso: riceve un pacchetto
versionato e hashato (doc `13_ModelRoles_Voice_Plan.md`). Contiene le direttive
canoniche non negoziabili di SEED, gli hash best-effort delle fonti e gli
artefatti della candidate (manifest, permission delta, diff, test report,
rollback plan).

`directive_pack_version` e' lo sha256 sull'insieme (direttive + fonti + feature +
scope + candidate). Se una fonte canonica o un artefatto cambia, il version
cambia: una review precedente diventa stale. Il pack e' privacy-safe: un secret
scan difensivo blocca la costruzione se gli artefatti contengono un segreto
evidente (le key restano solo in core_config, mai nel pack o nel prompt).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DIRECTIVE_SET_VERSION = "seed.directives.v1"

# Direttive canoniche estratte dai documenti SEED. `severity_floor` = gravita'
# minima quando la direttiva viene violata.
CANONICAL_DIRECTIVES: tuple[dict, ...] = (
    {"directive_id": "privacy.remote_payload_minimal",
     "source": "03_PrivacyGate.md",
     "text": "Qualunque contenuto remoto passa dal privacy gate; payload minimo e redatto.",
     "severity_floor": "blocking"},
    {"directive_id": "privacy.secrets_only_in_core_config",
     "source": "03_PrivacyGate.md",
     "text": "API key e segreti restano solo in core_config; mai in prompt, trace, lineage o audit.",
     "severity_floor": "blocking"},
    {"directive_id": "authority.generator_cannot_self_promote",
     "source": "11_Contratto_Mutazione.md",
     "text": "Chi genera una mutazione non puo auto-promuoverla; la review e' evidenza, non promotion authority.",
     "severity_floor": "blocking"},
    {"directive_id": "isolation.descendant_not_active_runtime",
     "source": "01_Architettura.md",
     "text": "Ogni cambiamento e' un descendant isolato valutato contro il parent, mai applicato in diretta.",
     "severity_floor": "blocking"},
    {"directive_id": "recovery.no_inplace_overwrite",
     "source": "04_Sandbox_Sicurezza.md",
     "text": "Nessun overwrite in-place dell'unico runtime funzionante; versioni recuperabili e rollback.",
     "severity_floor": "blocking"},
    {"directive_id": "permissions.effects_declared_and_approved",
     "source": "04_Sandbox_Sicurezza.md",
     "text": "Ogni variazione di autorita o permessi e' dichiarata e approvata.",
     "severity_floor": "high"},
    {"directive_id": "personality.compatible_not_mirror",
     "source": "09_Personalita_Compatibile.md",
     "text": "Adattamento espressivo, non copia di opinioni o identita dell'utente; il dissenso e' ammesso.",
     "severity_floor": "high"},
    {"directive_id": "hypotheses.distinct_from_facts",
     "source": "00_Visione_Prodotto.md",
     "text": "Ipotesi diverse dai fatti: provenance, confidenza, controevidenza e correzione.",
     "severity_floor": "medium"},
)

DIRECTIVE_IDS = frozenset(d["directive_id"] for d in CANONICAL_DIRECTIVES)

# Pattern di segreti evidenti: il pack non deve mai trasportarli verso il reviewer.
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),  # JWT-like
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*\S{8,}"),
)


class DirectivePackError(ValueError):
    """Il pack non puo' essere costruito (es. artefatti con un segreto)."""


@dataclass
class DesignDirectivePack:
    directive_pack_version: str
    directive_set_version: str
    feature: str
    scope: str
    directives: list[dict]
    sources: list[dict]          # [{path, sha256}]
    candidate: dict              # manifest / permission_delta / diff / test_report / rollback_plan
    assumptions: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    ui_directives: dict | None = None     # U7: sezione UI (P0-P5), se richiesta

    def to_dict(self) -> dict:
        out = {
            "directive_pack_version": self.directive_pack_version,
            "directive_set_version": self.directive_set_version,
            "feature": self.feature,
            "scope": self.scope,
            "directives": self.directives,
            "sources": self.sources,
            "candidate": self.candidate,
            "assumptions": self.assumptions,
            "conflicts": self.conflicts,
        }
        if self.ui_directives is not None:
            out["ui_directives"] = self.ui_directives
        return out


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _contains_secret(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)


def build_directive_pack(*, feature: str, scope: str, candidate: dict,
                         docs_dir: str | Path | None = None,
                         assumptions=(), conflicts=(),
                         include_ui_directives: bool = False) -> DesignDirectivePack:
    """Costruisce il pack. `docs_dir` opzionale: se presente, hasha le fonti
    canoniche (dev/repo); il runtime impacchettato puo' ometterlo e la
    versione resta determinata dall'insieme direttive in-code + candidate.

    U7: le mutation UI includono automaticamente `ui_directives` (P0-P5 +
    Guidelines complete). `include_ui_directives` resta un override esplicito."""
    candidate_str = json.dumps(candidate, sort_keys=True, ensure_ascii=False)
    if _contains_secret(candidate_str):
        raise DirectivePackError(
            "artefatti candidate contengono un possibile segreto: il pack e' bloccato")

    sources: list[dict] = []
    if docs_dir is not None:
        base = Path(docs_dir)
        for name in sorted({d["source"] for d in CANONICAL_DIRECTIVES}):
            path = base / name
            if path.exists():
                sources.append({"path": name, "sha256": _sha256_text(
                    path.read_text(encoding="utf-8"))})

    normalized_scope = scope.strip().lower().replace("-", "_")
    normalized_feature = feature.strip().lower()
    candidate_text = candidate_str.lower()
    touches_ui = (
        include_ui_directives
        or normalized_scope in {"ui", "ui_change", "ui_manifest", "interface"}
        or "ui_manifest" in candidate_text
        or "ui_change" in candidate_text
        or normalized_feature.startswith("ui")
    )
    ui_section = None
    if touches_ui:
        from .ui_governance import ui_directives_section
        ui_section = ui_directives_section()

    fingerprint = json.dumps({
        "set": DIRECTIVE_SET_VERSION,
        "directives": CANONICAL_DIRECTIVES,
        "sources": sources,
        "feature": feature,
        "scope": scope,
        "candidate": candidate,
        "ui_directives": ui_section,
    }, sort_keys=True, ensure_ascii=False)
    version = _sha256_text(fingerprint)

    pack = DesignDirectivePack(
        directive_pack_version=version,
        directive_set_version=DIRECTIVE_SET_VERSION,
        feature=feature,
        scope=scope,
        directives=[dict(d) for d in CANONICAL_DIRECTIVES],
        sources=sources,
        candidate=candidate,
        assumptions=list(assumptions),
        conflicts=list(conflicts),
    )
    if ui_section is not None:
        pack.ui_directives = ui_section
    return pack
