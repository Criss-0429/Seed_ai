"""D4 WRITE_SAFE: default OFF, approval owner, dry-run+rollback+observation,
auto-rollback su observation fallita, path allowlist workspace, audit aggregato."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core import write_safe as ws_mod  # noqa: E402
from seed.core.write_safe import (  # noqa: E402
    WriteRequest, WriteSafeError, WriteSafeWorker, build_workspace_note_worker,
    validate_write_safe, workspace_note_contract, workspace_path,
)
from seed.core.worker import ActionContract  # noqa: E402


class _AllowBroker:
    def authorize(self, *a, **k):
        return True


class _DenyBroker:
    def authorize(self, *a, **k):
        return False


def _enabled_worker(broker=None):
    return build_workspace_note_worker(
        broker=broker or _AllowBroker(), enabled=True,
        allowed_actions=("worker.write_workspace_note",))


# --- contract validation --------------------------------------------------
def test_validate_write_safe_requires_approval_dryrun_rollback():
    good = workspace_note_contract()
    validate_write_safe(good)
    with pytest.raises(WriteSafeError):
        validate_write_safe(ActionContract(
            name="x", description="", input_schema={}, output_schema={},
            risk_class="write", allowed_scopes=(), side_effect_type="write",
            requires_approval=False, supports_dry_run=True, supports_rollback=True,
            observability_signal="s"))


# --- default OFF + allowlist + approval -----------------------------------
def test_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    worker = build_workspace_note_worker(broker=_AllowBroker(), enabled=False)
    res = worker.run(WriteRequest(action="worker.write_workspace_note",
                                  arguments={"name": "n", "content": "x"},
                                  owner_approved=True))
    assert not res.ok and "disabilitato" in res.error


def test_owner_approval_required(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    worker = _enabled_worker()
    res = worker.run(WriteRequest(action="worker.write_workspace_note",
                                  arguments={"name": "n", "content": "x"},
                                  owner_approved=False))
    assert not res.ok and res.audit["denied"] is True


def test_non_allowlisted_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    worker = build_workspace_note_worker(broker=_AllowBroker(), enabled=True,
                                         allowed_actions=())
    res = worker.run(WriteRequest(action="worker.write_workspace_note",
                                  arguments={"name": "n", "content": "x"},
                                  owner_approved=True))
    assert not res.ok and "allowlist" in res.error


def test_permission_denied_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    worker = build_workspace_note_worker(
        broker=_DenyBroker(), enabled=True,
        allowed_actions=("worker.write_workspace_note",))
    res = worker.run(WriteRequest(action="worker.write_workspace_note",
                                  arguments={"name": "n", "content": "x"},
                                  owner_approved=True))
    assert not res.ok and res.audit["denied"] is True


# --- esecuzione reale + rollback + observation ----------------------------
def test_approved_write_creates_note_and_audits(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    events = []
    worker = build_workspace_note_worker(
        broker=_AllowBroker(), enabled=True,
        allowed_actions=("worker.write_workspace_note",),
        audit=lambda k, p: events.append((k, p)))
    res = worker.run(WriteRequest(action="worker.write_workspace_note",
                                  arguments={"name": "diary", "content": "ciao"},
                                  owner_approved=True))
    assert res.ok and not res.rolled_back
    assert Path(res.output["path"]).read_text(encoding="utf-8") == "ciao"
    payload = next(p for k, p in events if k == "worker_write_invoked")
    assert payload["write_actions"] == 1 and payload["rolled_back"] is False
    assert "ciao" not in json.dumps(events)        # contenuto mai nell'audit


def test_failed_observation_triggers_rollback(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    worker = WriteSafeWorker(broker=_AllowBroker(), enabled=True,
                             allowed_actions=("worker.bad",))
    written = {}

    def execute(args):
        p = workspace_path("notes", "bad.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("data", encoding="utf-8")
        written["p"] = p
        return {"path": str(p)}, (p, None)

    def rollback(token):
        p, _prev = token
        p.unlink(missing_ok=True)

    def observe(_a, _o):
        return {"observed": False}                  # observation fallisce

    worker.register(workspace_note_contract().__class__(
        name="worker.bad", description="", input_schema={}, output_schema={},
        risk_class="write", allowed_scopes=("workspace_notes",),
        side_effect_type="write", requires_approval=True, supports_dry_run=True,
        supports_rollback=True, observability_signal="x"),
        execute, rollback, observe)
    res = worker.run(WriteRequest(action="worker.bad", arguments={},
                                  owner_approved=True))
    assert not res.ok and res.rolled_back is True
    assert not written["p"].exists()                # rollback ha cancellato


# --- path allowlist -------------------------------------------------------
def test_workspace_path_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    with pytest.raises(WriteSafeError):
        workspace_path("..", "..", "escape.txt")


# --- review ----------------------------------------------------------------
def test_review_is_aggregate(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    worker = _enabled_worker()
    review = worker.review()
    assert review["destructive_forbidden"] is True
    assert review["requires_owner_approval"] is True
    assert review["path_allowlist"] == "workspace_only"
