"""Tests for S3 Descendant Builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.descendant import (  # noqa: E402
    DescendantBuildError,
    DescendantBuilder,
    DescendantIntegrityError,
)
from seed.core.lineage import MutationCandidate  # noqa: E402


def _candidate(**overrides) -> MutationCandidate:
    values = {
        "mutation_id": "mutation-ui",
        "parent_version": "parent-1",
        "reason": "Test isolated UI change",
        "evidence_refs": ["trace:1"],
        "hypothesis": "Warm accent improves readability",
        "target_scope": ["ui", "theme"],
        "expected_signals": [
            {"metric": "preference", "direction": "increase", "window": "3d"}
        ],
        "evaluation_plan": ["replay", "canary"],
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


class TestDescendantBuilder:
    def test_ui_build_isolated_and_reproducible(self, tmp_path):
        versions = tmp_path / "versions"
        parent = _parent(versions)
        builder = DescendantBuilder(tmp_path / "descendants", versions)
        candidate = _candidate()
        proposal = {
            "type": "ui_change",
            "target": "theme",
            "diff": {"accent": "#cc7722"},
        }

        path, manifest = builder.build(candidate, proposal)
        descendant_ui = json.loads(
            (path / "runtime" / "state" / "ui_manifest.json").read_text(encoding="utf-8"))
        parent_ui = json.loads(
            (parent / "state" / "ui_manifest.json").read_text(encoding="utf-8"))
        assert descendant_ui["theme"]["accent"] == "#cc7722"
        assert parent_ui["theme"]["accent"] == "#888888"
        assert manifest.active is False and manifest.executable is False

        rebuilt_path, rebuilt = builder.build(candidate, proposal)
        assert rebuilt_path == path
        assert rebuilt.content_hash == manifest.content_hash
        assert builder.verify(path) == manifest

    def test_tampering_detected(self, tmp_path):
        versions = tmp_path / "versions"
        _parent(versions)
        builder = DescendantBuilder(tmp_path / "descendants", versions)
        path, _ = builder.build(_candidate(), {
            "type": "ui_change", "target": "theme", "diff": {"accent": "#cc7722"},
        })
        target = path / "runtime" / "state" / "ui_manifest.json"
        target.write_text("{}", encoding="utf-8")
        with pytest.raises(DescendantIntegrityError, match="file hashes differ"):
            builder.verify(path)

    def test_manifest_contract_tampering_detected(self, tmp_path):
        versions = tmp_path / "versions"
        _parent(versions)
        builder = DescendantBuilder(tmp_path / "descendants", versions)
        path, _ = builder.build(_candidate(), {
            "type": "ui_change", "target": "theme", "diff": {"accent": "#cc7722"},
        })
        manifest_path = path / "descendant_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["parent_version"] = "forged-parent"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(DescendantIntegrityError, match="manifest contract differs"):
            builder.verify(path)

    def test_missing_parent_rejected(self, tmp_path):
        builder = DescendantBuilder(tmp_path / "descendants", tmp_path / "versions")
        with pytest.raises(DescendantBuildError, match="parent snapshot missing"):
            builder.build(_candidate(), {
                "type": "ui_change", "target": "theme", "diff": {"accent": "#cc7722"},
            })

    def test_parent_path_traversal_rejected(self, tmp_path):
        builder = DescendantBuilder(tmp_path / "descendants", tmp_path / "versions")
        with pytest.raises(DescendantBuildError, match="unsafe parent_version"):
            builder.build(_candidate(parent_version="../escape"), {
                "type": "ui_change", "target": "theme", "diff": {"accent": "#cc7722"},
            })

    def test_capability_is_audited_but_not_executed(self, tmp_path):
        versions = tmp_path / "versions"
        _parent(versions)
        builder = DescendantBuilder(tmp_path / "descendants", versions)
        candidate = _candidate(mutation_id="mutation-cap", target_scope=["capability"])
        proposal = {
            "type": "new_capability",
            "target": "echo_generated",
            "diff": {
                "manifest": {
                    "capability_id": "echo_generated",
                    "description": "echo",
                    "input_schema": {},
                    "risk_class": "safe",
                    "origin": "generated",
                },
                "code": "raise RuntimeError('must not execute during build')\n",
            },
        }
        path, _ = builder.build(candidate, proposal)
        audit = json.loads(
            (path / "runtime" / "capabilities" / "echo_generated" / "AUDIT.json")
            .read_text(encoding="utf-8"))
        assert audit == {
            "executed": False,
            "passed": True,
            "source": "S3 static audit only",
            "violations": [],
        }

    def test_unsafe_capability_id_rejected(self, tmp_path):
        versions = tmp_path / "versions"
        _parent(versions)
        builder = DescendantBuilder(tmp_path / "descendants", versions)
        candidate = _candidate(mutation_id="mutation-cap", target_scope=["capability"])
        with pytest.raises(DescendantBuildError, match="unsafe capability_id"):
            builder.build(candidate, {
                "type": "new_capability",
                "target": "../escape",
                "diff": {
                    "manifest": {
                        "capability_id": "../escape",
                        "description": "escape",
                        "input_schema": {},
                        "risk_class": "safe",
                        "origin": "generated",
                    },
                    "code": "print('{}')\n",
                },
            })

    @pytest.mark.parametrize(
        ("mutation_id", "proposal", "relative_path", "assertion"),
        [
            (
                "mutation-trait",
                {"type": "trait_change", "target": "interaction.verbosity",
                 "diff": {"value": 0.9}},
                "runtime/state/user_model.json",
                lambda data: data["interaction"]["verbosity"] == 0.9,
            ),
            (
                "mutation-persona",
                {"type": "persona_change", "target": "tone",
                 "diff": {"tone": "direct but independent"}},
                "runtime/state/ui_manifest.json",
                lambda data: data["persona"]["tone"] == "direct but independent",
            ),
            (
                "mutation-policy",
                {"type": "policy_change", "target": "quiet_hours",
                 "diff": {"trigger": "focus", "action": "silence"}},
                "runtime/state/policy.json",
                lambda data: data["rules"][0]["action"] == "silence",
            ),
            (
                "mutation-prune",
                {"type": "prune_capability", "target": "old_cap", "diff": {}},
                "runtime/overlays/pruned_capabilities.json",
                lambda data: data["capability_ids"] == ["old_cap"],
            ),
        ],
    )
    def test_supported_legacy_proposals_materialize(
        self, tmp_path, mutation_id, proposal, relative_path, assertion,
    ):
        versions = tmp_path / mutation_id / "versions"
        parent = _parent(versions)
        old_cap = parent / "capabilities" / "old_cap"
        old_cap.mkdir(parents=True)
        (old_cap / "manifest.json").write_text("{}", encoding="utf-8")
        builder = DescendantBuilder(tmp_path / mutation_id / "descendants", versions)
        candidate = _candidate(mutation_id=mutation_id)
        path, _ = builder.build(candidate, proposal)
        data = json.loads((path / relative_path).read_text(encoding="utf-8"))
        assert assertion(data)
        if proposal["type"] == "prune_capability":
            assert not (path / "runtime" / "capabilities" / "old_cap").exists()
