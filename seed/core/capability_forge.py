"""P7.0 Selective Capability Forge — contratti, policy e lifecycle (doc 19).

Questa fase e' SOLO fondazione: contratti V2 tipizzati, macchina a stati del
lifecycle, controllo deterministico e fail-closed dell'authority envelope, policy
di discard dei segreti e migrazione conservativa dei tool V1. **Nessun cambiamento
di comportamento runtime**: niente osservazione, niente build, niente attivazione.
Le fasi P7.1+ (evidence engine, fitness, connector vetting, builder, evaluator,
connection broker, activation authority, UX, manutenzione) restano separate e
owner-gated.

Invariante cardine (doc 19): **SEED non puo mai auto-espandere la propria
autorita.** L'attivazione automatica e' ammessa solo quando l'autorita richiesta
e' un sottoinsieme deterministico di quella gia' concessa; ogni confronto ambiguo
o incompleto FALLISCE CHIUSO. Segreti (password/token/cookie/recovery) sono
discard-only: mai in memoria, prompt, lineage, audit, evidenze o input dei tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SCHEMA_VERSION = "seed.capability-forge.v2"


class ForgeError(ValueError):
    """Violazione di un contratto/policy P7."""


class LifecycleError(ForgeError):
    """Transizione di lifecycle non ammessa (fail-closed)."""


# ==========================================================================
# Lifecycle (CapabilityLifecycleState) — FSM auditabile, nessun salto di gate
# ==========================================================================
LIFECYCLE_STATES = (
    "observed", "framed", "researching", "planned", "building", "evaluating",
    "shadow", "awaiting_connection", "canary", "active",
    "dormant", "quarantined", "rejected", "archived",
)
# Transizioni ammesse. quarantine/reject/archive sono raggiungibili da quasi
# ovunque (fail-safe); active richiede shadow->(awaiting_connection|canary).
_TRANSITIONS: dict[str, frozenset[str]] = {
    "observed": frozenset({"framed", "rejected", "archived"}),
    "framed": frozenset({"researching", "rejected", "archived"}),
    "researching": frozenset({"planned", "rejected", "archived"}),
    "planned": frozenset({"building", "rejected", "archived"}),
    "building": frozenset({"evaluating", "quarantined", "rejected", "archived"}),
    "evaluating": frozenset({"shadow", "quarantined", "rejected", "archived"}),
    "shadow": frozenset({"awaiting_connection", "canary", "quarantined",
                         "rejected", "archived"}),
    "awaiting_connection": frozenset({"canary", "active", "quarantined",
                                      "rejected", "archived"}),
    "canary": frozenset({"active", "dormant", "quarantined", "rejected", "archived"}),
    "active": frozenset({"dormant", "quarantined", "archived"}),
    "dormant": frozenset({"active", "quarantined", "archived"}),
    "quarantined": frozenset({"archived", "rejected"}),
    "rejected": frozenset(),
    "archived": frozenset(),
}


def can_transition(current: str, target: str) -> bool:
    if current not in _TRANSITIONS or target not in LIFECYCLE_STATES:
        return False
    return target in _TRANSITIONS[current]


def advance_lifecycle(current: str, target: str) -> str:
    """Valida e ritorna il nuovo stato. Fail-closed su stati/transizioni ignote."""
    if not can_transition(current, target):
        raise LifecycleError(f"transizione non ammessa: {current!r} -> {target!r}")
    return target


# ==========================================================================
# Secret discard policy (discard-only: mai persistito ne' usato)
# ==========================================================================
_SECRET_KEY = re.compile(
    r"(pass(word|wd)?|secret|token|api[_-]?key|cookie|session|bearer|"
    r"authorization|auth|recovery[_-]?code|private[_-]?key|client[_-]?secret|"
    r"refresh[_-]?token|access[_-]?token)", re.I)
# Valori dalla forma palese di segreto (jwt, bearer, chiavi lunghe).
_SECRET_VALUE = re.compile(
    r"(eyJ[A-Za-z0-9_\-]{10,}|Bearer\s+\S+|sk-[A-Za-z0-9]{16,}|"
    r"AKIA[0-9A-Z]{12,}|[A-Fa-f0-9]{40,})")


def looks_like_secret(key: str = "", value: str = "") -> bool:
    if key and _SECRET_KEY.search(key):
        return True
    return bool(value and _SECRET_VALUE.search(str(value)))


def discard_secrets(payload: dict) -> tuple[dict, int]:
    """Rimuove (discard-only) qualunque coppia che sembri un segreto, ricorsivo.
    Ritorna (payload_ripulito, numero_scartati). Non redige a placeholder: scarta."""
    discarded = 0
    out: dict = {}
    for key, value in (payload or {}).items():
        if isinstance(value, dict):
            sub, n = discard_secrets(value)
            discarded += n
            out[key] = sub
            continue
        if looks_like_secret(str(key), value if isinstance(value, str) else ""):
            discarded += 1
            continue
        out[key] = value
    return out, discarded


# ==========================================================================
# AuthorityEnvelope + subset check deterministico e FAIL-CLOSED
# ==========================================================================
@dataclass(frozen=True)
class AuthorityEnvelope:
    authority_id: str = ""
    connection_id: str = ""
    data_classes: frozenset[str] = field(default_factory=frozenset)
    effects: frozenset[str] = field(default_factory=frozenset)
    scopes: frozenset[str] = field(default_factory=frozenset)
    destinations: frozenset[str] = field(default_factory=frozenset)
    schedules: frozenset[str] = field(default_factory=frozenset)
    quantitative_limits: dict = field(default_factory=dict)
    valid_from: float | None = None
    expires_at: float | None = None
    revocation_ref: str = ""

    def validate(self) -> None:
        for name in ("data_classes", "effects", "scopes", "destinations", "schedules"):
            value = getattr(self, name)
            if not isinstance(value, (set, frozenset)):
                raise ForgeError(f"{name} deve essere un set (fail-closed): {value!r}")
        if not isinstance(self.quantitative_limits, dict):
            raise ForgeError("quantitative_limits deve essere dict")


_AUTHORITY_SET_FIELDS = ("data_classes", "effects", "scopes", "destinations", "schedules")


def authority_subset(requested: AuthorityEnvelope, granted: AuthorityEnvelope) -> dict:
    """Verifica `requested ⊆ granted` (strict_subset_or_equal) in modo deterministico
    e FAIL-CLOSED: qualunque campo sconosciuto, ambiguo o non rappresentabile rende
    l'esito non-within. Ritorna `{within_authority, escalations, reasons}`.

    Nessuna dimensione compensa l'altra: una sola escalation basta a fermare
    l'auto-attivazione (la nuova autorita' richiede consenso umano)."""
    escalations: list[str] = []
    try:
        requested.validate()
        granted.validate()
    except ForgeError as exc:
        return {"within_authority": False, "escalations": ["malformed"],
                "reasons": [str(exc)]}

    # La connessione deve coincidere: una connessione diversa = nuova autorita'.
    if requested.connection_id != granted.connection_id:
        escalations.append("connection")

    for name in _AUTHORITY_SET_FIELDS:
        req = getattr(requested, name)
        grn = getattr(granted, name)
        extra = set(req) - set(grn)
        if extra:
            escalations.append(name)

    # limiti quantitativi: ogni chiave richiesta deve esistere ed essere <=;
    # chiave assente in granted = sconosciuta -> fail closed.
    for key, req_val in requested.quantitative_limits.items():
        if key not in granted.quantitative_limits:
            escalations.append(f"limit:{key}:unknown")
            continue
        try:
            if float(req_val) > float(granted.quantitative_limits[key]):
                escalations.append(f"limit:{key}:exceeded")
        except (TypeError, ValueError):
            escalations.append(f"limit:{key}:unrepresentable")

    # scadenza: una validita' oltre quella concessa e' una nuova autorita'.
    if granted.expires_at is not None:
        if requested.expires_at is None or float(requested.expires_at) > float(granted.expires_at):
            escalations.append("expiry")

    within = not escalations
    return {
        "within_authority": within,
        "escalations": sorted(dict.fromkeys(escalations)),
        "reasons": ["subset_or_equal"] if within else ["authority_escalation"],
    }


# ==========================================================================
# Contratti pubblici V2 (doc 19) — tipizzati, con invarianti critici
# ==========================================================================
@dataclass(frozen=True)
class WorkflowEvidence:
    evidence_id: str
    source_kind: str
    activity_kind: str
    recurrence: int = 0
    duration: float = 0.0
    friction_signals: tuple[str, ...] = ()
    outcome_signals: tuple[str, ...] = ()
    sensitivity: str = "normal"          # normal | sensitive
    provenance_refs: tuple[str, ...] = ()
    local_feature_refs: tuple[str, ...] = ()
    raw_retention: str = "ephemeral"     # ephemeral salvo consenso esplicito
    created_at: float = 0.0
    expires_at: float | None = None

    def validate(self) -> None:
        if not self.evidence_id:
            raise ForgeError("evidence_id mancante")
        if self.raw_retention not in ("ephemeral", "consented"):
            raise ForgeError(f"raw_retention non ammesso: {self.raw_retention!r}")
        if self.sensitivity == "sensitive" and self.raw_retention != "ephemeral":
            raise ForgeError("evidenza sensibile non puo' trattenere raw")


@dataclass(frozen=True)
class NeedHypothesis:
    hypothesis_id: str
    user_goal: str
    observed_problem: str
    evidence_refs: tuple[str, ...] = ()
    counterevidence_refs: tuple[str, ...] = ()
    affected_contexts: tuple[str, ...] = ()
    expected_value: float = 0.0
    uncertainty: float = 1.0
    expiry: float | None = None

    def validate(self) -> None:
        if not self.hypothesis_id or not self.user_goal:
            raise ForgeError("ipotesi incompleta")
        if not 0.0 <= float(self.uncertainty) <= 1.0:
            raise ForgeError("uncertainty fuori range [0,1]")


_FITNESS_VERDICTS = frozenset({"do_nothing", "reuse", "connect", "build", "defer"})


@dataclass(frozen=True)
class FitnessDecision:
    decision_id: str
    need_hypothesis_ref: str
    alternatives: tuple[str, ...] = ()
    evidence_strength: float = 0.0
    expected_utility: float = 0.0
    privacy_cost: float = 0.0
    trust_cost: float = 0.0
    maintenance_cost: float = 0.0
    operational_risk: float = 0.0
    hard_blockers: tuple[str, ...] = ()
    selected_alternative: str = "do_nothing"
    verdict: str = "do_nothing"
    reasons: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.verdict not in _FITNESS_VERDICTS:
            raise ForgeError(f"verdict non ammesso: {self.verdict!r}")
        # Un blocker hard non e' compensabile da maggiore utilita'.
        if self.hard_blockers and self.verdict in ("build", "connect"):
            raise ForgeError("hard_blockers presenti: build/connect non ammessi")


_CONNECTOR_KINDS = frozenset({
    "existing_capability", "skill", "mcp_local", "mcp_remote", "official_api",
    "plugin", "file_exchange", "cli", "custom_adapter", "ui_automation",
})


@dataclass(frozen=True)
class ConnectorDescriptor:
    connector_id: str
    kind: str
    source: str = ""
    publisher: str = ""
    version: str = ""
    digest: str = ""
    dependency_lock_ref: str = ""
    tool_schema_hash: str = ""
    transport: str = ""
    destinations: tuple[str, ...] = ()
    credential_mode: str = "none"        # i tool generati non ricevono credenziali
    verification_state: str = "unverified"
    drift_policy: str = "quarantine"

    def validate(self) -> None:
        if self.kind not in _CONNECTOR_KINDS:
            raise ForgeError(f"connector kind non ammesso: {self.kind!r}")
        # connettori remoti/non fidati richiedono pinning prima dell'uso.
        if self.kind in ("mcp_remote", "mcp_local", "custom_adapter", "plugin") \
                and not self.digest:
            raise ForgeError(f"{self.kind}: digest/pinning obbligatorio")


@dataclass(frozen=True)
class ConnectionRequirement:
    connection_id: str
    human_reason: str
    service_name: str = ""
    data_access: tuple[str, ...] = ()
    allowed_effects: tuple[str, ...] = ()
    explicit_limits: tuple[str, ...] = ()
    denied_effects: tuple[str, ...] = ()
    retention: str = "local"
    revocation_path: str = ""

    def validate(self) -> None:
        # La UI mostra una richiesta comprensibile, non token/scope tecnici.
        if not self.human_reason:
            raise ForgeError("human_reason obbligatorio (linguaggio comprensibile)")
        if not self.revocation_path:
            raise ForgeError("revocation_path obbligatorio")


@dataclass(frozen=True)
class CapabilityPlan:
    capability_id: str
    need_hypothesis_ref: str
    selected_connector_ref: str
    requested_authority: AuthorityEnvelope
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    action_contracts: tuple[str, ...] = ()
    expected_observations: tuple[str, ...] = ()
    dry_run_plan: str = ""
    rollback_plan: str = ""
    evaluation_plan: str = ""
    maintenance_plan: str = ""

    def validate(self) -> None:
        if not self.capability_id:
            raise ForgeError("capability_id mancante")
        self.requested_authority.validate()
        if not self.rollback_plan:
            raise ForgeError("rollback_plan obbligatorio")


_EVAL_VERDICTS = frozenset({"pass", "inconclusive", "blocked"})


@dataclass(frozen=True)
class CapabilityEvaluationReport:
    capability_id: str
    manifest_digest: str
    evaluator_version: str = SCHEMA_VERSION
    deterministic_checks: bool = False
    adversarial_checks: bool = False
    privacy_checks: bool = False
    authority_checks: bool = False
    runtime_checks: bool = False
    dry_run_result: str = ""
    rollback_result: str = ""
    expected_observation_result: str = ""
    comparison_result: str = ""
    blockers: tuple[str, ...] = ()
    verdict: str = "inconclusive"

    def validate(self) -> None:
        if self.verdict not in _EVAL_VERDICTS:
            raise ForgeError(f"verdict eval non ammesso: {self.verdict!r}")
        # incertezza o prove mancanti non possono diventare approvazione implicita.
        if self.verdict == "pass" and self.blockers:
            raise ForgeError("verdict pass incompatibile con blockers aperti")

    @property
    def passed(self) -> bool:
        return self.verdict == "pass" and not self.blockers


@dataclass(frozen=True)
class CapabilityManifestV2:
    capability_id: str
    version: str
    description: str
    connector_ref: str
    requested_authority: AuthorityEnvelope
    provenance: str = ""
    evidence_refs: tuple[str, ...] = ()
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    action_contracts: tuple[str, ...] = ()
    risk_classes: tuple[str, ...] = ()
    data_classes: tuple[str, ...] = ()
    retention: str = "local"
    dependency_lock_ref: str = ""
    build_digest: str = ""
    tests: tuple[str, ...] = ()
    fixtures: tuple[str, ...] = ()
    health_check: str = ""
    expected_observations: tuple[str, ...] = ()
    dry_run_plan: str = ""
    rollback_plan: str = ""
    drift_policy: str = "quarantine"
    maintenance_policy: str = ""
    auto_activation: bool = False        # mai auto-attivo senza gate espliciti

    def validate(self) -> None:
        if not self.capability_id or not self.version:
            raise ForgeError("manifest incompleto")
        self.requested_authority.validate()


# ==========================================================================
# Migrazione V1 conservativa: i tool esistenti NON diventano auto-attivi
# ==========================================================================
def migrate_v1_capability(v1: dict) -> CapabilityManifestV2:
    """Mappa un descrittore capability V1 (registry legacy) in un manifest V2
    CONSERVATIVO: `auto_activation=False`, autorita' vuota (nessun envelope concesso),
    lifecycle non implicito. La migrazione non concede nulla: i tool legacy
    restano governati come prima e non si auto-attivano (doc 19 gate P7.0)."""
    cap_id = v1.get("capability_id") or v1.get("id") or ""
    if not cap_id:
        raise ForgeError("capability V1 senza id")
    manifest = CapabilityManifestV2(
        capability_id=cap_id,
        version=str(v1.get("version", "1")),
        description=v1.get("description", ""),
        connector_ref="existing_capability",
        requested_authority=AuthorityEnvelope(),   # vuoto: nessuna autorita' concessa
        provenance="migrated_v1",
        risk_classes=(v1.get("risk_class", "safe"),),
        auto_activation=False,                       # conservativo: mai auto-attivo
    )
    manifest.validate()
    return manifest
