"""R1-R7 local runtime completion contracts."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.brand import BrandEvolution  # noqa: E402
from seed.core.isolation import IsolationPolicy, backend_available, run_python  # noqa: E402
from seed.core.operations import OperationsError, OperationsManager  # noqa: E402
from seed.core.tool_builder import GovernedToolBuilder  # noqa: E402


def test_restricted_process_executes_json_contract_without_parent_env(tmp_path, monkeypatch):
    script = tmp_path / "tool.py"
    script.write_text(
        "import json,os,sys\n"
        "x=json.load(sys.stdin)\n"
        "print(json.dumps({'value':x['value'],'secret':os.getenv('SECRET_TEST')}))\n",
        encoding="utf-8")
    monkeypatch.setenv("SECRET_TEST", "must-not-leak")
    result = run_python(script, {"value": 7}, workspace=tmp_path / "work",
                        policy=IsolationPolicy())
    assert result.ok
    assert result.output == {"value": 7, "secret": None}
    assert backend_available("process") is True


def test_container_backend_fails_closed_when_unavailable(tmp_path, monkeypatch):
    script = tmp_path / "tool.py"
    script.write_text("print('{}')", encoding="utf-8")
    monkeypatch.setattr("seed.core.isolation.backend_available", lambda backend: False)
    result = run_python(script, {}, workspace=tmp_path / "work",
                        policy=IsolationPolicy(backend="container"))
    assert not result.ok and "unavailable" in result.stderr


def test_restricted_process_blocks_reads_outside_workspace(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("private", encoding="utf-8")
    script = tmp_path / "tool.py"
    script.write_text(
        "import json\n"
        f"print(json.dumps({{'value':open({str(secret)!r}).read()}}))\n",
        encoding="utf-8")
    result = run_python(script, {}, workspace=tmp_path / "work",
                        policy=IsolationPolicy())
    assert not result.ok
    assert "outside workspace" in result.stderr


def test_restricted_process_blocks_network_by_default(tmp_path):
    script = tmp_path / "tool.py"
    script.write_text(
        "import socket\n"
        "sock=socket.socket()\n"
        "sock.close()\n"
        "print('{}')\n",
        encoding="utf-8")
    result = run_python(script, {}, workspace=tmp_path / "work",
                        policy=IsolationPolicy())
    assert not result.ok
    assert "network disabled in isolated process" in result.stderr


def test_restricted_process_blocks_low_level_socket_bypass(tmp_path):
    script = tmp_path / "tool.py"
    script.write_text(
        "import _socket\n"
        "sock=_socket.socket()\n"
        "sock.close()\n"
        "print('{}')\n",
        encoding="utf-8")
    result = run_python(script, {}, workspace=tmp_path / "work",
                        policy=IsolationPolicy())
    assert not result.ok
    assert "network disabled in isolated process" in result.stderr


def test_restricted_process_allows_network_only_when_explicit(tmp_path):
    script = tmp_path / "tool.py"
    script.write_text(
        "import json,socket\n"
        "sock=socket.socket()\n"
        "sock.close()\n"
        "print(json.dumps({'socket_created':True}))\n",
        encoding="utf-8")
    result = run_python(script, {}, workspace=tmp_path / "work",
                        policy=IsolationPolicy(network_allowed=True))
    assert result.ok
    assert result.output == {"socket_created": True}


class _Registry:
    def __init__(self):
        self.installed = []

    def register_generated(self, manifest, code):
        self.installed.append((manifest, code))
        return True, []


def test_tool_builder_requires_owner_before_real_install(tmp_path):
    registry = _Registry()
    builder = GovernedToolBuilder(registry, tmp_path / "staging", enabled=True)
    manifest = {"capability_id": "echo.local", "description": "echo",
                "input_schema": {"value": "string"}, "risk_class": "safe",
                "origin": "generated"}
    code = ("import json,sys\nx=json.load(sys.stdin)\n"
            "print(json.dumps({'value':x.get('value')}))\n")
    candidate = builder.stage(manifest, code)
    assert candidate.audit_passed and candidate.test_passed
    assert builder.install(candidate, owner_approved=False, reviewer_passed=True)[0] is False
    assert builder.install(candidate, owner_approved=True, reviewer_passed=True)[0] is True
    assert len(registry.installed) == 1


class _Memory:
    def events_since(self, _since):
        return [{"kind": "onboarding_completed"}] * 12


def test_brand_hue_is_stable_and_maturity_comes_from_events():
    state = {"version": 0, "theme": {}}

    def writer(value):
        state.update(value)

    brand = BrandEvolution(_Memory(), lambda: state, writer)
    first = brand.refresh("utente")
    second = brand.refresh("utente")
    assert first["theme"]["hue"] == second["theme"]["hue"]
    assert first["theme"]["maturity"] == 0.5
    assert first["theme"]["chroma"] > 0.015


def _state(root: Path, marker: str):
    for name in ("state", "capabilities", "active", "lineage", "data"):
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "marker.txt").write_text(marker, encoding="utf-8")


def test_operations_backup_verify_restore_and_update_stage(tmp_path):
    root = tmp_path / "seed"
    _state(root, "before")
    ops = OperationsManager(root)
    backup = ops.create_backup()
    assert ops.verify_backup(backup)
    (root / "state" / "marker.txt").write_text("after", encoding="utf-8")
    with pytest.raises(OperationsError):
        ops.restore_backup(backup, owner_confirmed=False)
    ops.restore_backup(backup, owner_confirmed=True)
    assert (root / "state" / "marker.txt").read_text(encoding="utf-8") == "before"
    package = tmp_path / "update.bin"
    package.write_bytes(b"verified")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    staged = ops.stage_update(package, digest)
    assert staged.is_file()
    assert ops.schedule_update(staged, owner_confirmed=True).is_file()


def test_operations_migration_is_versioned_and_owner_gated(tmp_path):
    root = tmp_path / "seed"
    _state(root, "before")
    ops = OperationsManager(root)
    migrations = {1: lambda data_root: (data_root / "state" / "v1").write_text(
        "ok", encoding="utf-8")}
    with pytest.raises(OperationsError):
        ops.apply_migrations(migrations, target_version=1, owner_confirmed=False)
    assert ops.apply_migrations(migrations, target_version=1, owner_confirmed=True) == 1
    assert (root / "state" / "v1").is_file()


def test_uninstall_is_a_plan_not_an_automatic_delete(tmp_path):
    root = tmp_path / "seed"
    root.mkdir()
    plan = OperationsManager(root).uninstall_plan(remove_personal_data=True)
    assert plan["requires_owner_confirmation"] is True
    assert root.exists()
    with pytest.raises(OperationsError):
        OperationsManager(root).execute_uninstall(plan, owner_confirmed=False)
