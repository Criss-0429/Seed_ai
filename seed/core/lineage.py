"""Typed mutation contract and append-only lineage store.

This module is the first target-architecture boundary. It does not activate
mutations or change the legacy EvolutionEngine flow.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MUTATION_STATUSES = (
    "proposed",
    "built",
    "validating",
    "shadow",
    "canary",
    "promoted",
    "rolled_back",
    "rejected",
    "archived",
)

EVALUATION_OUTCOMES = ("pass", "fail", "inconclusive")

LINEAGE_EVENT_TYPES = (
    "candidate_created",
    "descendant_built",
    "status_transition",
    "evaluation_recorded",
    "design_review_recorded",   # S10.3: review reviewer come EVIDENZA, non promotion
    "exposure_started",
    "exposure_observation",
    "promotion_authorized",
    "promotion_decision",
    "rollback_recorded",
)

STATUS_TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"built", "rejected", "archived"},
    "built": {"validating", "rejected", "archived"},
    "validating": {"shadow", "canary", "rejected", "archived"},
    "shadow": {"canary", "rejected", "archived"},
    "canary": {"promoted", "rolled_back", "rejected", "archived"},
    "promoted": {"rolled_back", "archived"},
    "rolled_back": {"archived"},
    "rejected": {"archived"},
    "archived": set(),
}

_GENESIS_HASH = "0" * 64


class LineageError(ValueError):
    """Base error for mutation contract and lineage failures."""


class LineageIntegrityError(LineageError):
    """Raised when persisted lineage does not match its hash chain."""


class InvalidTransitionError(LineageError):
    """Raised when a mutation state transition is not allowed."""


@dataclass
class MutationCandidate:
    parent_version: str
    reason: str
    hypothesis: str
    target_scope: list[str]
    expected_signals: list[dict[str, Any]]
    evaluation_plan: list[str]
    rollback_plan: str
    evidence_refs: list[str] = field(default_factory=list)
    counterevidence_refs: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    permissions_delta: list[dict[str, Any] | str] = field(default_factory=list)
    expiry: str | None = None
    confidence: float = 0.0
    status: str = "proposed"
    mutation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: _utc_now())

    def validate(self) -> None:
        required_strings = {
            "mutation_id": self.mutation_id,
            "parent_version": self.parent_version,
            "created_at": self.created_at,
            "reason": self.reason,
            "hypothesis": self.hypothesis,
        }
        empty = [name for name, value in required_strings.items()
                 if not isinstance(value, str) or not value.strip()]
        if empty:
            raise LineageError(f"required string fields missing: {', '.join(empty)}")
        if self.status not in MUTATION_STATUSES:
            raise LineageError(f"unknown mutation status: {self.status}")
        if not 0.0 <= self.confidence <= 1.0:
            raise LineageError("confidence must be between 0 and 1")
        if not self.target_scope or not all(_nonempty_string(x) for x in self.target_scope):
            raise LineageError("target_scope must contain at least one non-empty value")
        if not isinstance(self.expected_signals, list):
            raise LineageError("expected_signals must be a list")
        for signal in self.expected_signals:
            if not isinstance(signal, dict):
                raise LineageError("each expected signal must be an object")
            missing = [key for key in ("metric", "direction", "window")
                       if not _nonempty_string(signal.get(key))]
            if missing:
                raise LineageError(
                    f"expected signal missing fields: {', '.join(missing)}")
        if not isinstance(self.evaluation_plan, list) or not all(
                _nonempty_string(x) for x in self.evaluation_plan):
            raise LineageError("evaluation_plan must be a list of non-empty values")
        for field_name in (
            "evidence_refs",
            "counterevidence_refs",
            "artifacts",
            "risks",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, list) or not all(_nonempty_string(x) for x in value):
                raise LineageError(f"{field_name} must be a list of non-empty values")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MutationCandidate":
        if not isinstance(data, dict):
            raise LineageError("candidate must be an object")
        try:
            candidate = cls(**data)
        except TypeError as exc:
            raise LineageError(f"invalid candidate fields: {exc}") from exc
        candidate.validate()
        return candidate


class LineageStore:
    """File-backed append-only lineage with a SHA-256 hash chain."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.events_dir = self.root / "events"
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def record_candidate(
        self,
        candidate: MutationCandidate,
        proposal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        candidate.validate()
        if candidate.status != "proposed":
            raise LineageError("new candidate must start in proposed status")
        if self.current_status(candidate.mutation_id) is not None:
            raise LineageError(f"candidate already exists: {candidate.mutation_id}")
        return self.append_event(
            "candidate_created",
            mutation_id=candidate.mutation_id,
            version_id=candidate.parent_version,
            payload={"candidate": candidate.to_dict(), "proposal": proposal or {}},
        )

    def proposal(self, mutation_id: str) -> dict[str, Any] | None:
        for event in self.events():
            if (event["mutation_id"] == mutation_id
                    and event["event_type"] == "candidate_created"):
                proposal = event["payload"].get("proposal")
                return proposal if isinstance(proposal, dict) else None
        return None

    def record_evaluation(
        self,
        mutation_id: str,
        evaluator_id: str,
        outcome: str,
        metrics: dict[str, Any] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        if self.current_status(mutation_id) is None:
            raise LineageError(f"unknown candidate: {mutation_id}")
        if not _nonempty_string(evaluator_id):
            raise LineageError("evaluator_id is required")
        if outcome not in EVALUATION_OUTCOMES:
            raise LineageError(f"unknown evaluation outcome: {outcome}")
        return self.append_event(
            "evaluation_recorded",
            mutation_id=mutation_id,
            payload={
                "evaluator_id": evaluator_id,
                "outcome": outcome,
                "metrics": metrics or {},
                "notes": notes,
            },
        )

    def record_descendant(
        self,
        mutation_id: str,
        artifact_ref: str,
        content_hash: str,
        files: dict[str, str],
    ) -> dict[str, Any]:
        if self.current_status(mutation_id) is None:
            raise LineageError(f"unknown candidate: {mutation_id}")
        if not _nonempty_string(artifact_ref) or not _nonempty_string(content_hash):
            raise LineageError("artifact_ref and content_hash are required")
        if not isinstance(files, dict) or not all(
                _nonempty_string(path) and _nonempty_string(digest)
                for path, digest in files.items()):
            raise LineageError("files must map paths to hashes")
        return self.append_event(
            "descendant_built",
            mutation_id=mutation_id,
            payload={
                "artifact_ref": artifact_ref,
                "content_hash": content_hash,
                "files": files,
            },
        )

    def record_exposure_start(
        self,
        mutation_id: str,
        phase: str,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_candidate(mutation_id)
        if phase not in {"shadow", "canary"}:
            raise LineageError(f"invalid exposure phase: {phase}")
        return self.append_event(
            "exposure_started",
            mutation_id=mutation_id,
            payload={"phase": phase, "policy": policy or {}},
        )

    def record_exposure_observation(
        self,
        mutation_id: str,
        phase: str,
        outcome: str,
        source: str,
        metrics: dict[str, Any] | None = None,
        blocking: bool = False,
        context_id: str = "",
    ) -> dict[str, Any]:
        self._require_candidate(mutation_id)
        if phase not in {"shadow", "canary"}:
            raise LineageError(f"invalid exposure phase: {phase}")
        if outcome not in EVALUATION_OUTCOMES:
            raise LineageError(f"invalid exposure outcome: {outcome}")
        if not _nonempty_string(source):
            raise LineageError("exposure observation source is required")
        return self.append_event(
            "exposure_observation",
            mutation_id=mutation_id,
            payload={
                "phase": phase,
                "outcome": outcome,
                "source": source,
                "metrics": metrics or {},
                "blocking": bool(blocking),
                "context_id": context_id,
            },
        )

    def authorize_promotion(
        self,
        mutation_id: str,
        authority_id: str,
        owner_approved: bool,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_candidate(mutation_id)
        if self.current_status(mutation_id) != "canary":
            raise LineageError("promotion authorization requires canary status")
        if not self.has_passing_evaluation(mutation_id):
            raise LineageError("promotion authorization requires passing evaluation")
        if not _nonempty_string(authority_id):
            raise LineageError("promotion authority_id is required")
        if not isinstance(evidence, dict) or not evidence:
            raise LineageError("promotion authorization evidence is required")
        required = {"evaluator", "shadow_passes", "canary_passes", "rollback_version"}
        if not required.issubset(evidence):
            raise LineageError("promotion authorization evidence incomplete")
        if evidence.get("shadow_passes", 0) < 1 or evidence.get("canary_passes", 0) < 1:
            raise LineageError("promotion authorization exposure evidence missing")
        return self.append_event(
            "promotion_authorized",
            mutation_id=mutation_id,
            payload={
                "authority_id": authority_id,
                "owner_approved": bool(owner_approved),
                "evidence": evidence,
            },
        )

    def record_promotion_decision(
        self,
        mutation_id: str,
        decision: str,
        reason: str,
        version_id: str = "",
    ) -> dict[str, Any]:
        self._require_candidate(mutation_id)
        if decision not in {"promote", "reject", "rollback"}:
            raise LineageError(f"invalid promotion decision: {decision}")
        if not _nonempty_string(reason):
            raise LineageError("promotion decision reason is required")
        return self.append_event(
            "promotion_decision",
            mutation_id=mutation_id,
            version_id=version_id,
            payload={"decision": decision, "reason": reason},
        )

    def record_rollback(
        self,
        mutation_id: str,
        restored_version: str,
        reason: str,
        automatic: bool,
    ) -> dict[str, Any]:
        self._require_candidate(mutation_id)
        if not _nonempty_string(restored_version) or not _nonempty_string(reason):
            raise LineageError("rollback restored_version and reason are required")
        return self.append_event(
            "rollback_recorded",
            mutation_id=mutation_id,
            version_id=restored_version,
            payload={"reason": reason, "automatic": bool(automatic)},
        )

    def transition(
        self,
        candidate: MutationCandidate,
        target_status: str,
        reason: str = "",
    ) -> MutationCandidate:
        candidate.validate()
        current = self.current_status(candidate.mutation_id)
        if current is None:
            raise LineageError(f"unknown candidate: {candidate.mutation_id}")
        recorded = self.candidate(candidate.mutation_id)
        if recorded is None:
            raise LineageError(f"candidate contract missing: {candidate.mutation_id}")
        if _candidate_contract(recorded) != _candidate_contract(candidate):
            raise LineageError(
                f"candidate contract differs from append-only record: {candidate.mutation_id}")
        if candidate.status != current:
            raise InvalidTransitionError(
                f"candidate status {candidate.status} does not match lineage status {current}")
        if target_status not in STATUS_TRANSITIONS[current]:
            raise InvalidTransitionError(f"transition not allowed: {current} -> {target_status}")
        if target_status == "promoted":
            blockers = self.promotion_blockers(candidate)
            if blockers:
                raise InvalidTransitionError(
                    f"promotion blocked: {', '.join(blockers)}")
        self.append_event(
            "status_transition",
            mutation_id=candidate.mutation_id,
            version_id=candidate.parent_version,
            payload={"from": current, "to": target_status, "reason": reason},
        )
        return replace(candidate, status=target_status)

    def candidate(self, mutation_id: str) -> MutationCandidate | None:
        candidate: MutationCandidate | None = None
        status: str | None = None
        for event in self.events():
            if event["mutation_id"] != mutation_id:
                continue
            if event["event_type"] == "candidate_created":
                candidate = MutationCandidate.from_dict(event["payload"]["candidate"])
                status = candidate.status
            elif event["event_type"] == "status_transition":
                status = event["payload"]["to"]
        return replace(candidate, status=status) if candidate is not None and status else candidate

    def promotion_blockers(self, candidate: MutationCandidate) -> list[str]:
        candidate.validate()
        blockers: list[str] = []
        if not candidate.evidence_refs:
            blockers.append("evidence_refs_missing")
        if not candidate.rollback_plan.strip():
            blockers.append("rollback_plan_missing")
        if not candidate.expected_signals:
            blockers.append("expected_signals_missing")
        if not candidate.evaluation_plan:
            blockers.append("evaluation_plan_missing")
        if not self.has_passing_evaluation(candidate.mutation_id):
            blockers.append("passing_evaluation_missing")
        if not self.has_promotion_authorization(candidate.mutation_id):
            blockers.append("promotion_authorization_missing")
        return blockers

    def has_passing_evaluation(self, mutation_id: str) -> bool:
        return any(
            event["event_type"] == "evaluation_recorded"
            and event["mutation_id"] == mutation_id
            and event["payload"].get("outcome") == "pass"
            for event in self.events()
        )

    def latest_evaluation_outcome(
        self,
        mutation_id: str,
        evaluator_id: str | None = None,
    ) -> str | None:
        outcome: str | None = None
        for event in self.events():
            if event["event_type"] != "evaluation_recorded":
                continue
            if event["mutation_id"] != mutation_id:
                continue
            if evaluator_id is not None and event["payload"].get("evaluator_id") != evaluator_id:
                continue
            outcome = event["payload"].get("outcome")
        return outcome

    def exposure_observations(
        self,
        mutation_id: str,
        phase: str,
    ) -> list[dict[str, Any]]:
        return [
            event["payload"]
            for event in self.events()
            if event["event_type"] == "exposure_observation"
            and event["mutation_id"] == mutation_id
            and event["payload"].get("phase") == phase
        ]

    def has_promotion_authorization(self, mutation_id: str) -> bool:
        return any(
            event["event_type"] == "promotion_authorized"
            and event["mutation_id"] == mutation_id
            for event in self.events()
        )

    def current_status(self, mutation_id: str) -> str | None:
        status: str | None = None
        for event in self.events():
            if event["mutation_id"] != mutation_id:
                continue
            if event["event_type"] == "candidate_created":
                status = event["payload"]["candidate"]["status"]
            elif event["event_type"] == "status_transition":
                status = event["payload"]["to"]
        return status

    def append_event(
        self,
        event_type: str,
        mutation_id: str = "",
        version_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if event_type not in LINEAGE_EVENT_TYPES:
            raise LineageError(f"unknown lineage event type: {event_type}")
        self.verify_integrity()
        prior = self.events()
        sequence = len(prior) + 1
        event = {
            "event_id": str(uuid.uuid4()),
            "sequence": sequence,
            "prev_hash": prior[-1]["event_hash"] if prior else _GENESIS_HASH,
            "event_type": event_type,
            "occurred_at": _utc_now(),
            "mutation_id": mutation_id,
            "version_id": version_id,
            "payload": payload or {},
        }
        event["event_hash"] = _event_hash(event)
        path = self.events_dir / f"{sequence:020d}-{event['event_id']}.json"
        _atomic_create_json(path, event)
        return event

    def _require_candidate(self, mutation_id: str) -> None:
        if self.current_status(mutation_id) is None:
            raise LineageError(f"unknown candidate: {mutation_id}")

    def events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for path in sorted(self.events_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise LineageIntegrityError(f"unreadable lineage event: {path.name}") from exc
            events.append(data)
        return events

    def verify_integrity(self) -> bool:
        previous_hash = _GENESIS_HASH
        for expected_sequence, event in enumerate(self.events(), start=1):
            if event.get("sequence") != expected_sequence:
                raise LineageIntegrityError(
                    f"invalid sequence at event {event.get('event_id')}")
            if event.get("prev_hash") != previous_hash:
                raise LineageIntegrityError(
                    f"invalid previous hash at sequence {expected_sequence}")
            if event.get("event_type") not in LINEAGE_EVENT_TYPES:
                raise LineageIntegrityError(
                    f"invalid event type at sequence {expected_sequence}")
            if event.get("event_hash") != _event_hash(event):
                raise LineageIntegrityError(
                    f"invalid event hash at sequence {expected_sequence}")
            previous_hash = event["event_hash"]
        return True


def _event_hash(event: dict[str, Any]) -> str:
    content = {key: value for key, value in event.items() if key != "event_hash"}
    canonical = json.dumps(
        content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _candidate_contract(candidate: MutationCandidate) -> dict[str, Any]:
    contract = candidate.to_dict()
    contract.pop("status", None)
    return contract


def _atomic_create_json(path: Path, data: dict[str, Any]) -> None:
    if path.exists():
        raise LineageError(f"append-only event already exists: {path.name}")
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".lineage-",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.flush()
        temp_path = Path(handle.name)
    try:
        if path.exists():
            raise LineageError(f"append-only event already exists: {path.name}")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
