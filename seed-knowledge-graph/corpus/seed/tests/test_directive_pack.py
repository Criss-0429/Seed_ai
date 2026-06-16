"""Test S10.2 Design Directive Pack: versione deterministica, stale su modifica,
secret scan difensivo, hashing fonti best-effort."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.directive_pack import (  # noqa: E402
    CANONICAL_DIRECTIVES,
    DIRECTIVE_IDS,
    DirectivePackError,
    build_directive_pack,
)

_CANDIDATE = {
    "manifest": {"mutation_id": "abc", "scope": "policy_change"},
    "permission_delta": [],
    "diff": "policy.json: +1 -0",
    "test_report": {"outcome": "pass"},
    "rollback_plan": "ripristina parent baseline-v1",
}


def _pack(candidate=None):
    return build_directive_pack(
        feature="S10 Model Role Separation", scope="policy_change",
        candidate=candidate or _CANDIDATE)


def test_pack_contains_canonical_directives():
    pack = _pack()
    ids = {d["directive_id"] for d in pack.directives}
    assert ids == set(DIRECTIVE_IDS)
    assert len(pack.directives) == len(CANONICAL_DIRECTIVES)


def test_pack_version_is_deterministic():
    assert _pack().directive_pack_version == _pack().directive_pack_version


def test_pack_version_changes_when_candidate_changes():
    other = dict(_CANDIDATE, diff="policy.json: +99 -0")
    assert _pack().directive_pack_version != _pack(other).directive_pack_version


def test_secret_in_candidate_blocks_pack():
    leaky = dict(_CANDIDATE, diff="api_key = sk-abcdef0123456789ZZZ")
    with pytest.raises(DirectivePackError):
        _pack(leaky)


def test_sources_hashed_when_docs_dir_present(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "03_PrivacyGate.md").write_text("contenuto privacy", encoding="utf-8")
    pack = build_directive_pack(
        feature="f", scope="s", candidate=_CANDIDATE, docs_dir=docs)
    paths = {s["path"] for s in pack.sources}
    assert "03_PrivacyGate.md" in paths
    assert all(len(s["sha256"]) == 64 for s in pack.sources)


def test_no_docs_dir_yields_empty_sources_but_stable_version():
    pack = _pack()
    assert pack.sources == []
    assert len(pack.directive_pack_version) == 64


def test_ui_scope_automatically_includes_ui_directives():
    pack = build_directive_pack(
        feature="mutation", scope="ui_change", candidate=_CANDIDATE)
    assert pack.ui_directives is not None
    assert pack.ui_directives["ui_directive_set_version"] == "seed.ui-directives.v2"
