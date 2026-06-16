"""Tests for S4 Replay And Evaluator Harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.descendant import DescendantBuilder  # noqa: E402
from seed.core.evaluator import (  # noqa: E402
    EvaluationError,
    EvaluationIntegrityError,
    EvaluatorHarness,
    ReplayAssertion,
    ReplayFixture,
    _scope_check,
)
from seed.core.lineage import LineageIntegrityError, LineageStore, MutationCandidate  # noqa: E402


def _candidate(**overrides) -> MutationCandidate:
    values = {
        "mutation_id": "mutation-ui",
        "parent_version": "parent-1",
        "reason": "Test deterministic evaluation",
        "evidence_refs": ["trace:redacted-1"],
        "hypothesis": "Warm accent improves readability",
        "target_scope": ["ui", "theme"],
        "expected_signals": [
            {"metric": "preference", "direction": "increase", "window": "3d"}
        ],
        "evaluation_plan": ["replay", "shadow"],
        "risks": ["safe"],
        "permissions_delta": [],
        "rollback_plan": "parent-1",
    }
    values.update(overrides)
    return MutationCandidate(**values)


def _parent(versions: Path) -> Path:
    parent = versions / "parent-1"
    state = parent / "state"
    state.mkdir(parents=True)
    (state / "ui_manifest.json").write_text(json.dumps({
        "version": 0,
        "theme": {"accent": "#888888", "background": "#111111"},
        "persona": {"tone": "neutral"},
        "widgets": ["chat"],
    }), encoding="utf-8")
    (state / "user_model.json").write_text(json.dumps({
        "interaction": {"verbosity": 0.5},
    }), encoding="utf-8")
    (state / "policy.json").write_text(json.dumps({
        "rules": [], "suppressions": [],
    }), encoding="utf-8")
    return parent


def _proposal(**overrides) -> dict:
    value = {
        "type": "ui_change",
        "target": "theme",
        "diff": {"accent": "#cc7722"},
        "reason": "Test deterministic evaluation",
        "expected_signal": "preference increases",
        "risk_class": "safe",
        "permissions_delta": [],
    }
    value.update(overrides)
    return value


def _harness(tmp_path) -> tuple[EvaluatorHarness, LineageStore, DescendantBuilder]:
    versions = tmp_path / "versions"
    _parent(versions)
    lineage = LineageStore(tmp_path / "lineage")
    builder = DescendantBuilder(tmp_path / "lab" / "descendants", versions)
    harness = EvaluatorHarness(
        lineage,
        builder,
        tmp_path / "lab" / "evaluator_runs",
        tmp_path / "lab" / "replay_fixtures",
    )
    return harness, lineage, builder


def _prepare(
    harness: EvaluatorHarness,
    lineage: LineageStore,
    builder: DescendantBuilder,
    candidate: MutationCandidate,
    proposal: dict,
) -> MutationCandidate:
    lineage.record_candidate(candidate, proposal=proposal)
    path, manifest = builder.build(candidate, proposal)
    lineage.record_descendant(
        candidate.mutation_id,
        artifact_ref=path.as_posix(),
        content_hash=manifest.content_hash,
        files=manifest.files,
    )
    return lineage.transition(candidate, "built", reason="test build")


class TestEvaluatorHarness:
    def test_ui_replay_pass_is_reproducible_and_not_active(self, tmp_path):
        harness, lineage, builder = _harness(tmp_path)
        proposal = _proposal()
        candidate = _prepare(harness, lineage, builder, _candidate(), proposal)

        report = harness.evaluate(candidate, proposal)
        assert report.outcome == "pass"
        assert not report.descendant_executed and not report.provider_called
        assert lineage.current_status(candidate.mutation_id) == "validating"
        assert lineage.has_passing_evaluation(candidate.mutation_id)
        assert harness.verify_report(candidate.mutation_id) == report

        repeated = harness.evaluate(lineage.candidate(candidate.mutation_id), proposal)
        assert repeated == report
        assert lineage.current_status(candidate.mutation_id) == "validating"

    def test_new_capability_is_inconclusive_and_never_executed(self, tmp_path):
        harness, lineage, builder = _harness(tmp_path)
        candidate = _candidate(
            mutation_id="mutation-cap",
            target_scope=["capability", "generated"],
        )
        proposal = _proposal(
            type="new_capability",
            target="generated_cap",
            diff={
                "manifest": {
                    "capability_id": "generated_cap",
                    "description": "must not execute",
                    "input_schema": {},
                    "risk_class": "safe",
                    "origin": "generated",
                },
                "code": (
                    "from pathlib import Path\n"
                    "Path('EXECUTED').write_text('yes')\n"
                ),
            },
        )
        candidate = _prepare(harness, lineage, builder, candidate, proposal)

        report = harness.evaluate(candidate, proposal)
        descendant = builder.descendants_root / candidate.mutation_id
        assert report.outcome == "inconclusive"
        assert not list(descendant.rglob("EXECUTED"))
        assert not lineage.has_passing_evaluation(candidate.mutation_id)
        assert lineage.current_status(candidate.mutation_id) == "validating"

    def test_permission_mismatch_fails_and_rejects(self, tmp_path):
        harness, lineage, builder = _harness(tmp_path)
        proposal = _proposal(permissions_delta=["network"])
        candidate = _prepare(harness, lineage, builder, _candidate(), proposal)

        report = harness.evaluate(candidate, proposal)
        assert report.outcome == "fail"
        assert lineage.current_status(candidate.mutation_id) == "rejected"

    def test_descendant_tampering_blocks_evaluation(self, tmp_path):
        harness, lineage, builder = _harness(tmp_path)
        proposal = _proposal()
        candidate = _prepare(harness, lineage, builder, _candidate(), proposal)
        target = builder.descendants_root / candidate.mutation_id / "runtime" / "state" / "ui_manifest.json"
        target.write_text("{}", encoding="utf-8")

        with pytest.raises(EvaluationIntegrityError, match="file hashes differ"):
            harness.evaluate(candidate, proposal)

    def test_lineage_tampering_blocks_evaluation(self, tmp_path):
        harness, lineage, builder = _harness(tmp_path)
        proposal = _proposal()
        candidate = _prepare(harness, lineage, builder, _candidate(), proposal)
        event_path = next(lineage.events_dir.glob("*.json"))
        event = json.loads(event_path.read_text(encoding="utf-8"))
        event["mutation_id"] = "forged"
        event_path.write_text(json.dumps(event), encoding="utf-8")

        with pytest.raises(LineageIntegrityError):
            harness.evaluate(candidate, proposal)

    def test_non_redacted_or_secret_fixture_rejected(self, tmp_path):
        harness, _, _ = _harness(tmp_path)
        ReplayFixture(
            fixture_id="raw",
            source="trace",
            redacted=False,
            assertions=[ReplayAssertion("a", "state/ui_manifest.json", "exists", "theme")],
        )
        with pytest.raises(EvaluationError, match="not redacted"):
            ReplayFixture(
                fixture_id="raw",
                source="trace",
                redacted=False,
                assertions=[ReplayAssertion("a", "state/ui_manifest.json", "exists", "theme")],
            ).validate()
        with pytest.raises(EvaluationError, match="private data or secret"):
            ReplayFixture(
                fixture_id="secret",
                source="trace",
                redacted=True,
                source_ref="mario.rossi@example.com",
                assertions=[ReplayAssertion("a", "state/ui_manifest.json", "exists", "theme")],
            ).validate()
        assert harness.load_fixtures() == []

    def test_external_replay_failure_rejects_candidate(self, tmp_path):
        harness, lineage, builder = _harness(tmp_path)
        fixture = ReplayFixture(
            fixture_id="hidden-regression",
            source="synthetic",
            redacted=True,
            assertions=[
                ReplayAssertion(
                    "accent-must-remain-old",
                    "state/ui_manifest.json",
                    "equals",
                    "theme.accent",
                    "#888888",
                )
            ],
        )
        (harness.replay_fixtures_root / "hidden.json").write_text(
            json.dumps(fixture.to_dict()), encoding="utf-8"
        )
        proposal = _proposal()
        candidate = _prepare(harness, lineage, builder, _candidate(), proposal)

        report = harness.evaluate(candidate, proposal)
        assert report.outcome == "fail"
        assert lineage.current_status(candidate.mutation_id) == "rejected"

    def test_report_tampering_detected(self, tmp_path):
        harness, lineage, builder = _harness(tmp_path)
        proposal = _proposal()
        candidate = _prepare(harness, lineage, builder, _candidate(), proposal)
        harness.evaluate(candidate, proposal)
        path = harness.evaluator_runs_root / f"{candidate.mutation_id}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["outcome"] = "fail"
        path.write_text(json.dumps(raw), encoding="utf-8")

        with pytest.raises(EvaluationIntegrityError, match="hash differs"):
            harness.verify_report(candidate.mutation_id)

    def test_fixture_path_traversal_rejected(self):
        with pytest.raises(EvaluationError, match="unsafe replay assertion file"):
            ReplayAssertion("escape", "../secret.json", "file_exists").validate()

    def test_scope_check_detects_extra_file(self, tmp_path):
        versions = tmp_path / "versions"
        parent = _parent(versions)
        runtime = tmp_path / "runtime"
        import shutil
        shutil.copytree(parent, runtime)
        state = json.loads((runtime / "state" / "ui_manifest.json").read_text(encoding="utf-8"))
        state["theme"]["accent"] = "#cc7722"
        (runtime / "state" / "ui_manifest.json").write_text(json.dumps(state), encoding="utf-8")
        (runtime / "state" / "policy.json").write_text('{"rules":[{"extra":true}]}', encoding="utf-8")

        check = _scope_check(parent, runtime, _proposal())
        assert check.outcome == "fail"
        assert "state/policy.json" in check.metrics["unexpected_files"]
