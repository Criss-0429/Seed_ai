"""P7.1-P7.5 + P7.9 engines del Selective Capability Forge (doc 19).

Tutti gli engine sono PURI e a dipendenze iniettate: nessuna rete/subprocess/os
nel modulo; scanner, runner e flussi reali vengono passati dal chiamante e restano
dietro i flag owner. Riusa i contratti P7.0 (`capability_forge`). Regola cardine:
il builder non promuove ne' attiva; l'autorita' non si auto-espande; segreti
discard-only; ogni confronto ambiguo fallisce chiuso.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from . import capability_forge as cf

_SENSITIVE_HINTS = ("salute", "health", "salary", "stipendio", "bank", "iban",
                    "medical", "diagnos", "password", "religione", "orientamento")


# ==========================================================================
# P7.1 — Local Evidence Engine (consent-gated, raw effimero, secret discard)
# ==========================================================================
class EvidenceError(cf.ForgeError):
    pass


def classify_sensitivity(text: str) -> str:
    low = (text or "").lower()
    return "sensitive" if any(h in low for h in _SENSITIVE_HINTS) else "normal"


@dataclass
class EvidenceEngine:
    """Comprende workflow SOLO da sorgenti con consenso esplicito. Il raw resta
    effimero: si scartano i segreti, si classifica la sensibilita', si derivano
    feature aggregate; il contenuto grezzo non viene mai trattenuto. Revoca = purge."""
    audit: object = None
    _consent: set[str] = field(default_factory=set)
    _evidence: dict[str, cf.WorkflowEvidence] = field(default_factory=dict)
    _seq: int = 0

    def _emit(self, kind, payload):
        if self.audit:
            self.audit(kind, payload)

    def grant(self, source: str, on: bool = True) -> None:
        if on:
            self._consent.add(source)
        else:
            self._consent.discard(source)
        self._emit("forge_consent", {"source": source, "enabled": bool(on)})

    def observe(self, source: str, activity_kind: str, raw: dict,
                *, has_local_safe_path: bool = True) -> cf.WorkflowEvidence | None:
        """Deriva WorkflowEvidence da un raw locale gia' disponibile. Fail-closed:
        sorgente non consentita o assenza di percorso locale sicuro -> nulla."""
        if source not in self._consent:
            self._emit("forge_observe_blocked", {"source": source, "reason": "no_consent"})
            return None
        if not has_local_safe_path:
            self._emit("forge_observe_blocked", {"source": source, "reason": "no_local_path"})
            return None
        clean, discarded = cf.discard_secrets(raw or {})
        sensitivity = classify_sensitivity(json.dumps(clean, ensure_ascii=True))
        # feature DERIVATE: conteggi e flag, mai testo grezzo persistito.
        friction = tuple(k for k in ("retry", "error", "manual", "slow") if clean.get(k))
        self._seq += 1
        eid = f"ev-{self._seq}"
        existing = [e for e in self._evidence.values()
                    if e.source_kind == source and e.activity_kind == activity_kind]
        ev = cf.WorkflowEvidence(
            evidence_id=eid, source_kind=source, activity_kind=activity_kind,
            recurrence=len(existing) + 1, friction_signals=friction,
            sensitivity=sensitivity, raw_retention="ephemeral",
            provenance_refs=(source,))
        ev.validate()
        self._evidence[eid] = ev
        # audit AGGREGATO: mai raw, mai segreti.
        self._emit("forge_evidence", {"evidence_id": eid, "source": source,
                   "activity": activity_kind, "sensitivity": sensitivity,
                   "secrets_discarded": discarded, "recurrence": ev.recurrence})
        return ev

    def revoke(self, source: str) -> int:
        """Interrompe la raccolta e PURGA le evidenze di quella sorgente."""
        self._consent.discard(source)
        purged = [eid for eid, e in self._evidence.items() if e.source_kind == source]
        for eid in purged:
            del self._evidence[eid]
        self._emit("forge_revoke", {"source": source, "purged": len(purged)})
        return len(purged)

    def evidence(self, activity_kind: str | None = None) -> list[cf.WorkflowEvidence]:
        items = list(self._evidence.values())
        return [e for e in items if activity_kind is None or e.activity_kind == activity_kind]


# ==========================================================================
# P7.2 — Need & Fitness Engine (no-op + alternative, multi-obiettivo)
# ==========================================================================
@dataclass
class NeedFitnessEngine:
    """Decide PRIMA se valga la pena intervenire, poi quale soluzione. Default =
    `do_nothing`. Le soglie di ricorrenza sono configurabili; la richiesta esplicita
    supera la ricorrenza ma non i gate; il feedback negativo sopprime proposte simili."""
    min_occurrences: int = 3
    min_sessions: int = 2
    sensitive_min_occurrences: int = 5
    sensitive_min_sessions: int = 3
    _suppressed: dict[str, float] = field(default_factory=dict)

    def suppress(self, goal: str, until: float) -> None:
        self._suppressed[goal] = until

    def frame_need(self, evidences: list[cf.WorkflowEvidence], *, user_goal: str,
                   observed_problem: str, sessions: int, now: float = 0.0,
                   explicit: bool = False) -> cf.NeedHypothesis | None:
        """Inquadra un bisogno solo con evidenza sufficiente (o richiesta esplicita).
        Soglie piu' alte per ambiti sensibili. Soppressioni attive bloccano."""
        if user_goal in self._suppressed and now < self._suppressed[user_goal]:
            return None
        sensitive = any(e.sensitivity == "sensitive" for e in evidences)
        occ = sum(e.recurrence for e in evidences)
        need_occ = self.sensitive_min_occurrences if sensitive else self.min_occurrences
        need_sess = self.sensitive_min_sessions if sensitive else self.min_sessions
        if not explicit and (occ < need_occ or sessions < need_sess):
            return None
        h = cf.NeedHypothesis(
            hypothesis_id=f"need-{abs(hash((user_goal, observed_problem)))}",
            user_goal=user_goal, observed_problem=observed_problem,
            evidence_refs=tuple(e.evidence_id for e in evidences),
            expected_value=min(1.0, occ / max(1, need_occ)),
            uncertainty=0.3 if explicit else 0.6)
        h.validate()
        return h

    def decide_fitness(self, need: cf.NeedHypothesis, *, alternatives: tuple[str, ...],
                       expected_utility: float, privacy_cost: float, trust_cost: float,
                       maintenance_cost: float, operational_risk: float,
                       hard_blockers: tuple[str, ...] = (),
                       evidence_strength: float = 0.0) -> cf.FitnessDecision:
        """Confronto multi-obiettivo. Le dimensioni restano separate: un blocker hard
        (privacy/autorita'/sicurezza) NON e' compensabile da maggiore utilita'.
        Default e ordine: do_nothing < reuse < connect < build."""
        need.validate()
        # ordine di preferenza: la soluzione piu' semplice adeguata vince.
        priority = ("do_nothing", "reuse", "connect", "build")
        chosen = "do_nothing"
        verdict = "do_nothing"
        reasons: list[str] = []
        if hard_blockers:
            reasons.append("hard_blockers_present")
        else:
            net = expected_utility - (privacy_cost + trust_cost + maintenance_cost
                                      + operational_risk)
            if net <= 0:
                reasons.append("value_not_above_cost")
            else:
                for alt in priority:
                    if alt in alternatives and alt != "do_nothing":
                        chosen = alt
                        verdict = alt
                        reasons.append("value_exceeds_cost")
                        break
                else:
                    reasons.append("no_adequate_alternative")
        d = cf.FitnessDecision(
            decision_id=f"fit-{need.hypothesis_id}", need_hypothesis_ref=need.hypothesis_id,
            alternatives=tuple(alternatives), evidence_strength=evidence_strength,
            expected_utility=expected_utility, privacy_cost=privacy_cost,
            trust_cost=trust_cost, maintenance_cost=maintenance_cost,
            operational_risk=operational_risk, hard_blockers=tuple(hard_blockers),
            selected_alternative=chosen, verdict=verdict, reasons=tuple(reasons))
        d.validate()
        return d


# ==========================================================================
# P7.3 — Connector Discovery & Vetting (pinning, scan, drift -> quarantena)
# ==========================================================================
class ConnectorError(cf.ForgeError):
    pass


@dataclass
class ConnectorVetter:
    """Un registry e' discovery, non fiducia. Prima dell'uso: pinning digest/schema,
    allowlist destinazioni (anti-SSRF/egress), scansione iniettata (segreti, token
    passthrough, scope eccessivo). Drift di digest/schema -> quarantena."""
    allowed_destinations: frozenset[str] = field(default_factory=frozenset)
    _pins: dict[str, tuple[str, str]] = field(default_factory=dict)

    def vet(self, desc: cf.ConnectorDescriptor, *, scan=None) -> dict:
        desc.validate()
        blocking: list[str] = []
        extra_dest = set(desc.destinations) - set(self.allowed_destinations)
        if extra_dest:
            blocking.append("destinations_not_allowlisted")     # SSRF/egress
        findings = list(scan(desc)) if scan else []
        for f in findings:
            blocking.append(f"scan:{f}")                        # token_passthrough/ssrf/scope...
        if not desc.digest:
            blocking.append("missing_digest")
        state = "verified" if not blocking else "blocked"
        if state == "verified":
            self._pins[desc.connector_id] = (desc.digest, desc.tool_schema_hash)
        return {"connector_id": desc.connector_id, "verification_state": state,
                "blocking": sorted(dict.fromkeys(blocking))}

    def check_drift(self, desc: cf.ConnectorDescriptor) -> dict:
        pin = self._pins.get(desc.connector_id)
        if pin is None:
            return {"drift": False, "quarantine": False, "reason": "not_pinned"}
        drift = (desc.digest, desc.tool_schema_hash) != pin
        return {"drift": drift, "quarantine": drift,
                "reason": "digest_or_schema_changed" if drift else "stable"}


# ==========================================================================
# P7.4 — Capability Builder V2 (isolato; niente credenziali, niente ambiente)
# ==========================================================================
@dataclass
class CapabilityBuilderV2:
    """Riceve un `CapabilityPlan`, NON accesso libero al sistema. Produce un
    manifest V2 riproducibile: chiama solo handle tipizzati del connector, non
    importa SDK nel runtime, non installa dipendenze, non riceve credenziali, non
    puo' promuovere/attivare (non ha riferimenti a vault/activation/promotion)."""

    def build(self, plan: cf.CapabilityPlan, *, connector: cf.ConnectorDescriptor,
              version: str = "1") -> cf.CapabilityManifestV2:
        plan.validate()
        connector.validate()
        # nessun segreto puo' entrare negli schema del manifest.
        _, leaked = cf.discard_secrets({**plan.input_schema, **plan.output_schema})
        if leaked:
            raise cf.ForgeError("schema contiene segreti: build rifiutata")
        digest = hashlib.sha256(json.dumps({
            "cap": plan.capability_id, "conn": connector.connector_id,
            "in": plan.input_schema, "out": plan.output_schema,
            "actions": plan.action_contracts}, sort_keys=True).encode()).hexdigest()
        manifest = cf.CapabilityManifestV2(
            capability_id=plan.capability_id, version=version,
            description=f"capability per {plan.need_hypothesis_ref}",
            connector_ref=connector.connector_id,
            requested_authority=plan.requested_authority,
            input_schema=plan.input_schema, output_schema=plan.output_schema,
            action_contracts=plan.action_contracts,
            dependency_lock_ref=connector.dependency_lock_ref,
            build_digest=digest, expected_observations=plan.expected_observations,
            dry_run_plan=plan.dry_run_plan, rollback_plan=plan.rollback_plan,
            auto_activation=False)
        manifest.validate()
        return manifest


# ==========================================================================
# P7.5 — Independent Evaluator (deterministico; inconclusive di default)
# ==========================================================================
@dataclass
class IndependentEvaluator:
    """Indipendente da builder/connector/activation. Prove mancanti o incertezza
    producono `inconclusive`, MAI approvazione implicita. Un solo blocker -> blocked."""

    def evaluate(self, manifest: cf.CapabilityManifestV2, *, checks: dict,
                 blockers: tuple[str, ...] = ()) -> cf.CapabilityEvaluationReport:
        manifest.validate()
        required = ("deterministic", "adversarial", "privacy", "authority", "runtime")
        all_pass = all(bool(checks.get(k)) for k in required)
        if blockers:
            verdict = "blocked"
        elif all_pass and manifest.build_digest:
            verdict = "pass"
        else:
            verdict = "inconclusive"
        report = cf.CapabilityEvaluationReport(
            capability_id=manifest.capability_id, manifest_digest=manifest.build_digest,
            deterministic_checks=bool(checks.get("deterministic")),
            adversarial_checks=bool(checks.get("adversarial")),
            privacy_checks=bool(checks.get("privacy")),
            authority_checks=bool(checks.get("authority")),
            runtime_checks=bool(checks.get("runtime")),
            blockers=tuple(blockers), verdict=verdict)
        report.validate()
        return report


# ==========================================================================
# P7.9 — Maintenance & monitoring (drift/quarantena/dormienza/pruning)
# ==========================================================================
@dataclass
class MaintenanceMonitor:
    """Confronta esito reale ed expected observation. Drift di autorita'/schema o
    comportamento inatteso -> quarantena; affidabilita' degradata -> dormienza/
    rollback. Il pruning rimuove solo artefatti generati; lineage resta."""
    _reliability: dict[str, list[bool]] = field(default_factory=dict)

    def record_outcome(self, cap_id: str, *, expected: str, observed: str,
                       authority_changed: bool = False) -> dict:
        ok = expected == observed and not authority_changed
        self._reliability.setdefault(cap_id, []).append(ok)
        if authority_changed:
            return {"state": "quarantined", "reason": "authority_drift"}
        if not ok:
            recent = self._reliability[cap_id][-3:]
            if recent.count(False) >= 2:
                return {"state": "dormant", "reason": "degraded_reliability"}
            return {"state": "active", "reason": "single_miss"}
        return {"state": "active", "reason": "expected_observation_met"}

    def reliability(self, cap_id: str) -> float:
        runs = self._reliability.get(cap_id, [])
        return round(sum(runs) / len(runs), 3) if runs else 1.0
