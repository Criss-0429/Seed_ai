"""D3: sandbox hardening per le azioni worker (doc 16).

Aggiunge sopra il sandbox esistente (`sandbox.py`: AST audit + subprocess isolato
senza key, CWD workspace, timeout, kill albero) il livello di GOVERNANCE che le
azioni non-read dovranno attraversare:

- **tier di isolamento** per azione: `in_process_read` (letture D2),
  `restricted_subprocess` (runner con env minimo e filesystem workspace-only),
  `container` (Docker read-only/cap-drop/resource limits, fail-closed);
- **trust gate**: `destructive` vietata; `write`/`execute`/`network` o
  `requires_approval` -> richiedono approval owner esplicito; observability bassa
  -> blocco (mai azione cieca);
- **dry-run obbligatorio prima del reale** per le azioni con effetti;
- **expected observation** dichiarata (active inference) e verificata;
- **rollback** richiesto per gli effetti reversibili.

D3 non abilita scrittura: fornisce il gate che D4 (WRITE_SAFE) usera'. Le letture
D2 passano dal gate senza approval (read-only, safe).
"""

from __future__ import annotations

from dataclasses import dataclass

from .isolation import backend_available

SCHEMA_VERSION = "seed.worker-sandbox.v1"

ISOLATION_TIERS = ("in_process_read", "restricted_subprocess", "container")

# Rischi che richiedono approval owner (trust gate).
_APPROVAL_RISK = frozenset({"write", "execute", "network"})
# Rischio vietato (mai instanziabile, coerente con permissions.FORBIDDEN).
_CRITICAL_RISK = frozenset({"destructive"})

# Soglia minima di observability: sotto questa, l'azione e' cieca -> blocco.
MIN_OBSERVABILITY = 0.0


class SandboxError(ValueError):
    pass


@dataclass(frozen=True)
class SandboxPolicy:
    isolation_tier: str
    network_allowed: bool = False
    path_allowlist: tuple[str, ...] = ()
    require_dry_run_first: bool = True
    require_rollback_for_writes: bool = True
    container_available: bool = False

    def validate(self) -> None:
        if self.isolation_tier not in ISOLATION_TIERS:
            raise SandboxError(f"isolation_tier sconosciuto: {self.isolation_tier!r}")


def select_isolation_tier(contract) -> str:
    """Tier deterministico per side_effect. Letture in-process; effetti reali
    nel subprocess ristretto; il caller puo' richiedere il container."""
    if contract.side_effect_type == "read":
        return "in_process_read"
    return "restricted_subprocess"


@dataclass(frozen=True)
class TrustGateResult:
    allowed: bool
    requires_owner_approval: bool
    blocked_reason: str | None
    reasons: tuple[str, ...]


def evaluate_trust_gate(contract, *, owner_approved: bool = False,
                        observability: float = 1.0,
                        policy: SandboxPolicy | None = None) -> TrustGateResult:
    """Decide se un'azione worker puo' procedere. Deterministico e spiegabile.

    - `destructive` -> bloccata (vietata in SEED);
    - observability sotto soglia -> bloccata (niente azione cieca);
    - effetti reali / risk write|execute|network / requires_approval ->
      richiedono approval owner esplicito;
    - tier `container` senza backend disponibile -> bloccato (degrada chiuso)."""
    if contract.risk_class in _CRITICAL_RISK:
        return TrustGateResult(False, False, "destructive_forbidden",
                               ("destructive_forbidden",))

    if observability < MIN_OBSERVABILITY or not contract.observability_signal:
        return TrustGateResult(False, False, "observability_too_low",
                               ("observability_too_low",))

    tier = select_isolation_tier(contract)
    if tier == "container" and not (policy and policy.container_available):
        return TrustGateResult(False, False, "container_backend_unavailable",
                               ("container_backend_unavailable",))

    needs_approval = (
        contract.side_effect_type != "read"
        or contract.risk_class in _APPROVAL_RISK
        or contract.requires_approval
    )
    if needs_approval and not owner_approved:
        return TrustGateResult(False, True, "owner_approval_required",
                               ("owner_approval_required",))

    reasons = ("trust_ok",) if not needs_approval else ("trust_ok", "owner_approved")
    return TrustGateResult(True, needs_approval, None, reasons)


def requires_rollback(contract, policy: SandboxPolicy) -> bool:
    """Gli effetti reversibili (write) richiedono un rollback dichiarato."""
    return (policy.require_rollback_for_writes
            and contract.side_effect_type != "read"
            and contract.supports_rollback is False)


def dry_run_required_first(contract, policy: SandboxPolicy) -> bool:
    """Le azioni con effetti devono avere una dry-run prima del reale."""
    return policy.require_dry_run_first and contract.side_effect_type != "read"


def expected_observation_ok(observation: dict | None) -> bool:
    """Active inference: dopo l'azione deve esserci un segnale osservato."""
    return bool(observation) and bool(observation.get("observed"))


def review_matrix() -> dict:
    """Snapshot rivedibile del gate (per owner/UI). Nessun dato personale."""
    return {
        "schema_version": SCHEMA_VERSION,
        "isolation_tiers": list(ISOLATION_TIERS),
        "approval_required_risk": sorted(_APPROVAL_RISK),
        "forbidden_risk": sorted(_CRITICAL_RISK),
        "min_observability": MIN_OBSERVABILITY,
        "container_available": backend_available("container"),
        "restricted_process_available": backend_available("process"),
        "dry_run_first_for_effects": True,
        "rollback_required_for_writes": True,
    }
