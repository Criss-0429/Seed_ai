"""Tests for S5 Shadow, Canary And Promotion core."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.descendant import DescendantBuilder  # noqa: E402
from seed.core.evaluator import EvaluatorHarness  # noqa: E402
from seed.core.lineage import InvalidTransitionError, LineageStore, MutationCandidate  # noqa: E402
from seed.core.promotion import PromotionAuthority, PromotionError, PromotionPolicy  # noqa: E402


def _candidate(**overrides) -> MutationCandidate:
    values = {
        "mutation_id": "mutation-policy",
        "parent_version": "parent-1",
        "reason": "Reduce interruptions during focus",
        "evidence_refs": ["trace:redacted-1"],
        "hypothesis": "Focus policy reduces unwanted interruption",
        "target_scope": ["policy"],
        "expected_signals": [
            {"metric": "interruptions", "direction": "decrease", "window": "3d"}
        ],
        "evaluation_plan": ["replay", "shadow", "canary"],
        "risks": ["safe"],
        "permissions_delta": [],
        "rollback_plan": "parent-1",
    }
    values.update(overrides)
    return MutationCandidate(**values)


def _proposal(**overrides) -> dict:
    value = {
        "type": "policy_change",
        "target": "focus",
        "diff": {"trigger": "focus", "action": "silence"},
        "reason": "Reduce interruptions during focus",
        "expected_signal": "interruptions decrease",
        "risk_class": "safe",
        "permissions_delta": [],
    }
    value.update(overrides)
    return value


def _parent(versions: Path) -> Path:
    parent = versions / "parent-1"
    state = parent / "state"
    state.mkdir(parents=True)
    (state / "policy.json").write_text(
        json.dumps({"rules": [], "suppressions": []}), encoding="utf-8"
    )
    (state / "user_model.json").write_text(
        json.dumps({"interaction": {"verbosity": 0.5}}), encoding="utf-8"
    )
    (state / "ui_manifest.json").write_text(
        json.dumps({"theme": {"accent": "#888888"}, "persona": {"tone": "neutral"}}),
        encoding="utf-8",
    )
    return parent


def _authority(tmp_path) -> tuple[PromotionAuthority, LineageStore, DescendantBuilder, EvaluatorHarness]:
    versions = tmp_path / "versions"
    parent = _parent(versions)
    state_dir = tmp_path / "state"
    shutil.copytree(parent / "state", state_dir)
    lineage = LineageStore(tmp_path / "lineage")
    descendants = DescendantBuilder(tmp_path / "lab" / "descendants", versions)
    evaluator = EvaluatorHarness(
        lineage,
        descendants,
        tmp_path / "lab" / "evaluator_runs",
        tmp_path / "lab" / "replay_fixtures",
    )
    authority = PromotionAuthority(
        lineage,
        descendants,
        evaluator,
        state_dir,
        tmp_path / "capabilities",
        versions,
        tmp_path / "active",
        tmp_path / "lab" / "canary_leases",
        policy=PromotionPolicy(min_shadow_passes=2, min_canary_passes=2),
    )
    return authority, lineage, descendants, evaluator


def _prepare_validating(
    authority: PromotionAuthority,
    lineage: LineageStore,
    descendants: DescendantBuilder,
    evaluator: EvaluatorHarness,
    candidate: MutationCandidate,
    proposal: dict,
) -> MutationCandidate:
    lineage.record_candidate(candidate, proposal=proposal)
    path, manifest = descendants.build(candidate, proposal)
    lineage.record_descendant(
        candidate.mutation_id, path.as_posix(), manifest.content_hash, manifest.files
    )
    candidate = lineage.transition(candidate, "built", reason="test build")
    report = evaluator.evaluate(candidate, proposal)
    assert report.outcome == "pass"
    return lineage.candidate(candidate.mutation_id)


def _prepare_canary(
    authority: PromotionAuthority,
    lineage: LineageStore,
    descendants: DescendantBuilder,
    evaluator: EvaluatorHarness,
    candidate: MutationCandidate | None = None,
    proposal: dict | None = None,
    *,
    owner_approved: bool = False,
) -> MutationCandidate:
    candidate = _prepare_validating(
        authority, lineage, descendants, evaluator,
        candidate or _candidate(), proposal or _proposal(),
    )
    candidate = authority.start_shadow(candidate)
    authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-a")
    authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-b")
    authority.start_canary(
        candidate, ["ctx-1"], owner_approved=owner_approved, ttl_seconds=3600
    )
    authority.observe(candidate.mutation_id, "canary", "pass", "canary-a", context_id="ctx-1")
    authority.observe(candidate.mutation_id, "canary", "pass", "canary-b", context_id="ctx-1")
    return lineage.candidate(candidate.mutation_id)


class TestPromotionAuthority:
    def test_pass_opens_shadow_without_activation(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _prepare_validating(
            authority, lineage, descendants, evaluator, _candidate(), _proposal()
        )
        before = (authority.state_dir / "policy.json").read_text(encoding="utf-8")

        shadow = authority.start_shadow(candidate)

        assert shadow.status == "shadow"
        assert (authority.state_dir / "policy.json").read_text(encoding="utf-8") == before
        assert lineage.exposure_observations(candidate.mutation_id, "shadow") == []

    def test_shadow_blocker_prevents_canary(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = authority.start_shadow(_prepare_validating(
            authority, lineage, descendants, evaluator, _candidate(), _proposal()
        ))
        authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-a")
        authority.observe(
            candidate.mutation_id, "shadow", "fail", "shadow-b", blocking=True
        )

        with pytest.raises(PromotionError, match="shadow_blocking_observation"):
            authority.start_canary(candidate, ["ctx-1"])

    def test_canary_lease_routes_only_allowed_context(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = authority.start_shadow(_prepare_validating(
            authority, lineage, descendants, evaluator, _candidate(), _proposal()
        ))
        authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-a")
        authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-b")
        lease = authority.start_canary(candidate, ["ctx-1"])

        canary_state = authority.state_dir_for_context("ctx-1")
        active_state = authority.state_dir_for_context("other")
        assert lease.active_for("ctx-1")
        assert canary_state != authority.state_dir
        assert active_state == authority.state_dir
        policy = json.loads((canary_state / "policy.json").read_text(encoding="utf-8"))
        assert policy["rules"][0]["action"] == "silence"

    def test_expired_canary_lease_does_not_route(self, tmp_path, monkeypatch):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = authority.start_shadow(_prepare_validating(
            authority, lineage, descendants, evaluator, _candidate(), _proposal()
        ))
        authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-a")
        authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-b")
        lease = authority.start_canary(candidate, ["ctx-1"], ttl_seconds=10)
        monkeypatch.setattr("seed.core.promotion.time.time", lambda: lease.expires_at + 1)

        assert authority.state_dir_for_context("ctx-1") == authority.state_dir
        with pytest.raises(PromotionError, match="no active lease"):
            authority.observe(
                candidate.mutation_id, "canary", "pass", "late", context_id="ctx-1"
            )

    def test_direct_lineage_promotion_without_authority_blocked(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _prepare_canary(authority, lineage, descendants, evaluator)

        with pytest.raises(InvalidTransitionError, match="promotion_authorization_missing"):
            lineage.transition(candidate, "promoted")

    def test_owner_gate_for_high_impact_or_permission_delta(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _candidate(
            target_scope=["policy", "privacy"],
            permissions_delta=["network"],
        )
        proposal = _proposal(permissions_delta=["network"])
        candidate = authority.start_shadow(_prepare_validating(
            authority, lineage, descendants, evaluator, candidate, proposal
        ))
        authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-a")
        authority.observe(candidate.mutation_id, "shadow", "pass", "shadow-b")

        with pytest.raises(PromotionError, match="owner_approval_missing"):
            authority.start_canary(candidate, ["ctx-1"])
        lease = authority.start_canary(candidate, ["ctx-1"], owner_approved=True)
        assert lease.active_for("ctx-1")

    def test_promotion_applies_state_and_writes_pointer(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _prepare_canary(authority, lineage, descendants, evaluator)
        notifications = []
        authority.on_runtime_changed = lambda: notifications.append("reload")

        promoted = authority.promote(candidate)

        assert promoted.status == "promoted"
        policy = json.loads((authority.state_dir / "policy.json").read_text(encoding="utf-8"))
        assert policy["rules"][0]["action"] == "silence"
        pointer = json.loads(
            (authority.active_root / "current_version.json").read_text(encoding="utf-8")
        )
        assert pointer["version_id"] == candidate.mutation_id
        assert (authority.versions_dir / candidate.mutation_id / "state").is_dir()
        assert authority.lease(candidate.mutation_id) is None
        assert notifications == ["reload"]

    def test_rollback_restores_parent(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        notifications = []
        authority.on_runtime_changed = lambda: notifications.append("reload")
        candidate = authority.promote(
            _prepare_canary(authority, lineage, descendants, evaluator)
        )

        rolled_back = authority.rollback(candidate, "manual test rollback")

        assert rolled_back.status == "rolled_back"
        policy = json.loads((authority.state_dir / "policy.json").read_text(encoding="utf-8"))
        assert policy["rules"] == []
        pointer = json.loads(
            (authority.active_root / "current_version.json").read_text(encoding="utf-8")
        )
        assert pointer["version_id"] == "parent-1"
        assert notifications == ["reload", "reload"]

    def test_stale_parent_blocks_promotion(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _prepare_canary(authority, lineage, descendants, evaluator)
        (authority.state_dir / "policy.json").write_text(
            json.dumps({"rules": [{"external": True}]}), encoding="utf-8"
        )

        assert "active_parent_stale" in authority.promotion_blockers(candidate)
        with pytest.raises(PromotionError, match="active_parent_stale"):
            authority.promote(candidate)

    def test_tampered_descendant_blocks_promotion(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _prepare_canary(authority, lineage, descendants, evaluator)
        target = descendants.descendants_root / candidate.mutation_id / "runtime" / "state" / "policy.json"
        target.write_text("{}", encoding="utf-8")

        assert "descendant_integrity_failed" in authority.promotion_blockers(candidate)

    def test_activation_failure_restores_parent_and_records_rollback(
        self, tmp_path, monkeypatch,
    ):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _prepare_canary(authority, lineage, descendants, evaluator)

        def broken_activate(runtime):
            (authority.state_dir / "policy.json").write_text(
                json.dumps({"rules": [{"broken": True}]}), encoding="utf-8"
            )
            raise RuntimeError("activation exploded")

        monkeypatch.setattr(authority, "_activate_runtime", broken_activate)
        with pytest.raises(PromotionError, match="parent restored"):
            authority.promote(candidate)

        policy = json.loads((authority.state_dir / "policy.json").read_text(encoding="utf-8"))
        assert policy["rules"] == []
        assert lineage.current_status(candidate.mutation_id) == "rolled_back"

    def test_rollback_failure_restores_promoted_state_and_pointer(
        self, tmp_path, monkeypatch,
    ):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        promoted = authority.promote(
            _prepare_canary(authority, lineage, descendants, evaluator)
        )
        original_activate = authority._activate_runtime

        def broken_parent_activate(runtime):
            if runtime.name == "parent-1":
                (authority.state_dir / "policy.json").write_text(
                    json.dumps({"rules": [{"half_rollback": True}]}), encoding="utf-8"
                )
                raise RuntimeError("rollback exploded")
            original_activate(runtime)

        monkeypatch.setattr(authority, "_activate_runtime", broken_parent_activate)
        with pytest.raises(PromotionError, match="prior active state restored"):
            authority.rollback(promoted, "test failed rollback")

        policy = json.loads((authority.state_dir / "policy.json").read_text(encoding="utf-8"))
        pointer = json.loads(
            (authority.active_root / "current_version.json").read_text(encoding="utf-8")
        )
        assert policy["rules"][0]["action"] == "silence"
        assert pointer["version_id"] == promoted.mutation_id
        assert lineage.current_status(promoted.mutation_id) == "promoted"

    def test_ui_and_personality_promotion_deferred(self, tmp_path):
        authority, lineage, descendants, evaluator = _authority(tmp_path)
        candidate = _candidate(
            mutation_id="mutation-ui",
            target_scope=["ui"],
        )
        proposal = _proposal(
            type="ui_change",
            target="theme",
            diff={"accent": "#cc7722"},
        )
        candidate = _prepare_canary(
            authority, lineage, descendants, evaluator, candidate, proposal
        )

        assert "proposal_type_not_state_promotable" in authority.promotion_blockers(candidate)
        with pytest.raises(PromotionError, match="proposal_type_not_state_promotable"):
            authority.promote(candidate)
