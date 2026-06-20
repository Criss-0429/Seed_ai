"""Collegamento end-to-end alla UI: i manager esistenti (tool builder, mutation
lifecycle, operations, delega) esposti via app.ui_* + JsApi, owner-gated."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.ui.shell import JsApi  # noqa: E402


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    return SeedApp(SeedConfig())


# --- tool builder -> UI ---------------------------------------------------
def test_tool_candidates_listed_and_install_gated(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    # candidate sintetica nello staging (audit/test passati)
    cap = "echo_tool"
    d = app.tool_builder.staging_root / cap
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps({
        "capability_id": cap, "description": "echo", "input_schema": {},
        "risk_class": "safe", "origin": "generated"}), encoding="utf-8")
    (d / "tool.py").write_text("print('{}')", encoding="utf-8")
    (d / "REVIEW.json").write_text(json.dumps({
        "capability_id": cap, "audit_passed": True, "test_passed": True,
        "violations": []}), encoding="utf-8")

    cands = app.ui_tool_candidates()
    assert any(c["capability_id"] == cap for c in cands)
    # senza owner approval -> non installa (gate)
    res = app.ui_tool_install(cap, owner_approved=False)
    assert res["ok"] is False
    app.shutdown()


def test_tool_install_rejects_path_traversal(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    res = app.ui_tool_install("../escape", owner_approved=True)
    assert res["ok"] is False and "inesistente" in res["error"]
    app.shutdown()


# --- mutation lifecycle -> UI ---------------------------------------------
def test_mutation_status_shape(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    status = app.ui_mutation_status()
    assert "enabled" in status and "proposals" in status and "owner_gate" in status
    assert isinstance(app.ui_advance_mutations(), list)   # nessuna candidate -> []
    app.shutdown()


# --- operations -> UI -----------------------------------------------------
def test_operations_status_and_backup(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    ops = app.ui_operations()
    assert "backups" in ops and ops["pending_update"] is False
    assert ops["uninstall_plan"]["requires_owner_confirmation"] is True
    path = app.ui_create_backup()
    assert Path(path).is_dir()
    assert Path(path).name in app.ui_operations()["backups"]
    app.shutdown()


def test_promote_mutation_gated(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    # mutation inesistente
    assert app.ui_promote_mutation("nope", True)["ok"] is False
    app.shutdown()


def test_delegation_status(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    st = app.ui_delegation_status()
    assert "enabled" in st and st["owner_gate"] is True
    app.shutdown()


# --- JsApi espone i metodi alla UI ----------------------------------------
def test_jsapi_exposes_system_methods(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    js = JsApi(app)
    assert isinstance(js.tool_candidates(), list)
    assert isinstance(js.mutation_status(), dict)
    assert isinstance(js.operations_status(), dict)
    assert isinstance(js.update_status(), dict)
    assert js.update_start(False)["ok"] is False
    assert isinstance(js.delegation_status(), dict)
    assert "errors" in js.tool_install("nope", False) or js.tool_install("nope", False)["ok"] is False
    app.shutdown()
