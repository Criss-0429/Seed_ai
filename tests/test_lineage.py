"""Tests for S1 Lineage Foundation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.lineage import (  # noqa: E402
    InvalidTransitionError,
    LineageError,
    LineageIntegrityError,
    LineageStore,
    MutationCandidate,
)


def _candidate(**overrides) -> MutationCandidate:
    values = {
        "mutation_id": "mutation-1",
        "parent_version": "version-1",
        "reason": "Repeated correction on planning output",
        "evidence_refs": ["trace:1"],
        "hypothesis": "Structured planning reduces correction rate",
        "target_scope": ["workflow"],
        "artifacts": ["diff:abc"],
        "expected_signals": [
            {"metric": "correction_rate", "direction": "decrease", "window": "3d"}
        ],
        "evaluation_plan": ["replay", "shadow"],
        "risks": ["workflow_regression"],
        "permissions_delta": [],
        "rollback_plan": "version-1",
        "confidence": 0.7,
    }
    values.update(overrides)
    return MutationCandidate(**values)


class TestMutationCandidate:
    def test_roundtrip(self):
        candidate = _candidate()
        assert MutationCandidate.from_dict(candidate.to_dict()) == candidate

    def test_invalid_confidence_rejected(self):
        with pytest.raises(LineageError, match="confidence"):
            _candidate(confidence=1.1).validate()

    def test_expected_signal_contract_enforced(self):
        with pytest.raises(LineageError, match="expected signal missing fields"):
            _candidate(expected_signals=[{"metric": "task_success"}]).validate()


class TestLineageStore:
    def test_candidate_and_events_are_append_only(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        candidate = _candidate()
        proposal = {"type": "ui_change", "diff": {"accent": "#cc7722"}}
        store.record_candidate(candidate, proposal=proposal)
        store.record_evaluation(candidate.mutation_id, "replay-v1", "pass",
                                metrics={"task_success": 1.0})

        events = store.events()
        assert [event["sequence"] for event in events] == [1, 2]
        assert events[1]["prev_hash"] == events[0]["event_hash"]
        assert store.proposal(candidate.mutation_id) == proposal
        assert store.verify_integrity()

    def test_duplicate_candidate_rejected(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        candidate = _candidate()
        store.record_candidate(candidate)
        with pytest.raises(LineageError, match="already exists"):
            store.record_candidate(candidate)

    def test_invalid_transition_rejected(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        candidate = _candidate()
        store.record_candidate(candidate)
        with pytest.raises(InvalidTransitionError, match="not allowed"):
            store.transition(candidate, "promoted")

    def test_promotion_requires_evidence_rollback_and_passing_evaluation(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        candidate = _candidate(evidence_refs=[], rollback_plan="")
        store.record_candidate(candidate)
        candidate = store.transition(candidate, "built")
        candidate = store.transition(candidate, "validating")
        candidate = store.transition(candidate, "shadow")
        candidate = store.transition(candidate, "canary")

        with pytest.raises(InvalidTransitionError, match="evidence_refs_missing"):
            store.transition(candidate, "promoted")

        ready = _candidate(mutation_id="mutation-ready")
        store.record_candidate(ready)
        ready = store.transition(ready, "built")
        ready = store.transition(ready, "validating")
        ready = store.transition(ready, "shadow")
        ready = store.transition(ready, "canary")
        store.record_evaluation(ready.mutation_id, "replay-v1", "pass")
        store.authorize_promotion(
            ready.mutation_id,
            "test-authority",
            owner_approved=False,
            evidence={
                "evaluator": "replay-v1",
                "shadow_passes": 1,
                "canary_passes": 1,
                "rollback_version": "version-1",
            },
        )
        promoted = store.transition(ready, "promoted")
        assert promoted.status == "promoted"
        assert store.current_status(ready.mutation_id) == "promoted"

    def test_candidate_contract_cannot_change_during_transition(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        candidate = _candidate()
        store.record_candidate(candidate)
        changed = _candidate(reason="Rewritten reason")
        with pytest.raises(LineageError, match="contract differs"):
            store.transition(changed, "built")

    def test_tampering_detected(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        store.record_candidate(_candidate())
        path = next(store.events_dir.glob("*.json"))
        event = json.loads(path.read_text(encoding="utf-8"))
        event["payload"]["candidate"]["reason"] = "tampered"
        path.write_text(json.dumps(event), encoding="utf-8")

        with pytest.raises(LineageIntegrityError, match="invalid event hash"):
            store.verify_integrity()

    def test_unknown_candidate_evaluation_rejected(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        with pytest.raises(LineageError, match="unknown candidate"):
            store.record_evaluation("missing", "replay-v1", "pass")

    def test_descendant_artifact_recorded(self, tmp_path):
        store = LineageStore(tmp_path / "lineage")
        candidate = _candidate()
        store.record_candidate(candidate)
        event = store.record_descendant(
            candidate.mutation_id,
            artifact_ref="lab/descendants/mutation-1",
            content_hash="a" * 64,
            files={"candidate.json": "b" * 64},
        )
        assert event["event_type"] == "descendant_built"
        assert event["payload"]["content_hash"] == "a" * 64
        assert store.verify_integrity()
