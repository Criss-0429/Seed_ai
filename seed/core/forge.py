"""P7 orchestrator: collega gli engine del Selective Capability Forge e li espone
al runtime, gated da `capability_forge.enabled` (default OFF).

Glue, non nuova policy: il vault usa il cipher locale (DPAPI), l'audit passa da
`memory.add_event` (aggregato, mai segreti), e ogni operazione e' fail-closed se la
capability e' disabilitata. La superficie P7.8 mostra cosa SEED ha imparato/deciso
e i controlli (pausa, revoca, restringi, dimentica, sopprimi, rollback).
"""

from __future__ import annotations

from .forge_runtime import (
    EvidenceEngine, NeedFitnessEngine, ConnectorVetter, CapabilityBuilderV2,
    IndependentEvaluator, MaintenanceMonitor,
)
from .forge_connection import CredentialVault, ConnectionBroker, ActivationAuthority


class CapabilityForge:
    """Orchestratore P7. Default OFF: con `enabled=False` espone solo stato e non
    osserva, costruisce o attiva nulla."""

    def __init__(self, cfg, memory, *, encrypt=None, decrypt=None):
        self.cfg = cfg
        self.memory = memory
        audit = (lambda kind, payload: memory.add_event(kind, payload)) if memory else None
        self.evidence = EvidenceEngine(audit=audit)
        self.fitness = NeedFitnessEngine(
            min_occurrences=cfg.observation_min_occurrences,
            min_sessions=cfg.observation_min_sessions,
            sensitive_min_occurrences=cfg.sensitive_min_occurrences,
            sensitive_min_sessions=cfg.sensitive_min_sessions)
        self.vetter = ConnectorVetter()
        self.builder = CapabilityBuilderV2()
        self.evaluator = IndependentEvaluator()
        self.vault = CredentialVault(encrypt=encrypt, decrypt=decrypt)
        self.broker = ConnectionBroker(vault=self.vault, audit=audit)
        self.activation = ActivationAuthority(
            auto_activation_enabled=cfg.auto_activation_enabled, audit=audit)
        self.maintenance = MaintenanceMonitor()
        self._timeline: list[dict] = []

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.enabled)

    # --- stato + timeline (P7.8) ---------------------------------------
    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_activation_enabled": bool(self.cfg.auto_activation_enabled),
            "evidence_count": len(self.evidence.evidence()),
            "learned": len(self._timeline),
            "thresholds": {
                "occurrences": self.cfg.observation_min_occurrences,
                "sessions": self.cfg.observation_min_sessions,
                "sensitive_occurrences": self.cfg.sensitive_min_occurrences,
            },
        }

    def timeline(self) -> list[dict]:
        """`SEED ha imparato/deciso X perche...`: spiegazione comprensibile, senza
        token/scope/manifest. Anche `non imparare` e' un esito mostrato."""
        return list(self._timeline)

    def record_decision(self, *, capability_id: str, state: str, why: str,
                        can_read: tuple[str, ...] = (), cannot: tuple[str, ...] = ()) -> dict:
        entry = {"capability_id": capability_id, "state": state, "why": why,
                 "can_read": list(can_read), "cannot": list(cannot)}
        self._timeline.append(entry)
        if self.memory:
            self.memory.add_event("forge_decision",
                                  {"capability_id": capability_id, "state": state})
        return entry

    # --- controlli utente (P7.8) ---------------------------------------
    def grant_observation(self, source: str, on: bool = True) -> dict:
        if not self.enabled:
            return {"ok": False, "reason": "forge_disabled"}
        self.evidence.grant(source, on)
        return {"ok": True, "source": source, "enabled": bool(on)}

    def forget_source(self, source: str) -> dict:
        purged = self.evidence.revoke(source)
        return {"ok": True, "purged": purged}

    def suppress_learning(self, goal: str, until: float) -> dict:
        self.fitness.suppress(goal, until)
        return {"ok": True, "goal": goal, "until": until}

    def revoke_connection(self, connection_id: str) -> dict:
        return {"ok": self.broker.revoke(connection_id)}
