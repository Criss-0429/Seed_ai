"""Tests for S6 Stable Boot Supervisor."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import seed.supervisor as supervisor_module  # noqa: E402
from seed import supervisor_cli  # noqa: E402
from seed.core import forbidden  # noqa: E402
from seed.core.lineage import LineageStore  # noqa: E402
from seed.supervisor import (  # noqa: E402
    BootSupervisor,
    SubprocessRuntimeLauncher,
    SupervisorError,
    SupervisorPolicy,
    VersionIntegrityError,
    emit_health_signal_from_env,
)


class FakeProcess:
    def __init__(self, exit_code: int | None = None):
        self.exit_code = exit_code
        self.terminated = False

    def poll(self) -> int | None:
        return self.exit_code

    def terminate(self) -> None:
        self.terminated = True
        self.exit_code = -15

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        return self.exit_code or 0


class FakeLauncher:
    def __init__(self, modes: dict[str, str] | None = None):
        self.modes = modes or {}
        self.calls: list[str] = []
        self.processes: list[FakeProcess] = []

    def __call__(self, version_id: str, health_file: Path, token: str) -> FakeProcess:
        self.calls.append(version_id)
        mode = self.modes.get(version_id, "healthy")
        process = FakeProcess(7 if mode == "crash" else None)
        self.processes.append(process)
        if mode in {"healthy", "invalid"}:
            health_file.parent.mkdir(parents=True, exist_ok=True)
            health_file.write_text(
                json.dumps(
                    {
                        "schema_version": "seed.health-signal.v1",
                        "version_id": version_id,
                        "token_sha256": hashlib.sha256(
                            (token if mode == "healthy" else "wrong").encode("utf-8")
                        ).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
        return process


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _active_state(root: Path, marker: str) -> None:
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    _write_json(state / "policy.json", {"marker": marker, "rules": []})
    _write_json(state / "user_model.json", {"marker": marker, "interaction": {}})
    _write_json(state / "ui_manifest.json", {"marker": marker, "theme": {}})
    capabilities = root / "capabilities"
    capabilities.mkdir(parents=True, exist_ok=True)
    (capabilities / "marker.txt").write_text(marker, encoding="utf-8")


def _supervisor(root: Path, timeout: float = 0.05) -> BootSupervisor:
    return BootSupervisor(
        root,
        SupervisorPolicy(health_timeout_seconds=timeout, poll_interval_seconds=0.005),
    )


def test_register_current_version_and_healthy_boot_mark_known_good(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)

    supervisor.register_current_version("v1")
    result = supervisor.boot(FakeLauncher())

    assert result.status == "healthy"
    assert result.fallback_used is False
    assert supervisor.active_version() == "v1"
    assert supervisor.known_good().version_id == "v1"
    assert (root / "versions" / "v1" / "state" / "policy.json").is_file()


def test_supervisor_normalizes_relative_root_before_cwd_changes(tmp_path, monkeypatch):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    monkeypatch.chdir(tmp_path)
    supervisor = _supervisor(Path("seed"))
    supervisor.register_current_version("v1")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    result = supervisor.boot(FakeLauncher())

    assert result.status == "healthy"
    assert supervisor.root == root.resolve()


@pytest.mark.parametrize(
    "pointer",
    [
        {"schema_version": "wrong", "version_id": "v1"},
        {"schema_version": "seed.active-version.v1", "version_id": "../escape"},
        {"schema_version": "seed.active-version.v1", "version_id": "missing"},
    ],
)
def test_invalid_active_pointer_blocks_before_launch(tmp_path, pointer):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")
    _write_json(root / "active" / "current_version.json", pointer)
    launcher = FakeLauncher()

    result = supervisor.boot(launcher)

    assert result.status == "blocked"
    assert launcher.calls == []


def test_corrupt_version_json_blocks_before_launch(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")
    (root / "versions" / "v1" / "state" / "policy.json").write_text(
        "{broken", encoding="utf-8"
    )

    result = supervisor.boot(FakeLauncher())

    assert result.status == "blocked"
    assert "invalid" in result.reason


def test_register_accepts_windows_utf8_bom_json(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    policy = root / "state" / "policy.json"
    policy.write_text('{"rules":[]}', encoding="utf-8-sig")
    supervisor = _supervisor(root)

    supervisor.register_current_version("v1")

    assert supervisor.active_version() == "v1"


def test_corrupt_lineage_blocks_before_launch(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")
    lineage = LineageStore(root / "lineage")
    lineage.append_event("promotion_decision", payload={"decision": "test"})
    event_path = next((root / "lineage" / "events").glob("*.json"))
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["payload"]["decision"] = "tampered"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    launcher = FakeLauncher()

    result = supervisor.boot(launcher)

    assert result.status == "blocked"
    assert "lineage integrity failed" in result.reason
    assert launcher.calls == []


@pytest.mark.parametrize(
    ("mode", "reason"),
    [("crash", "process exited before health"), ("invalid", "health signal invalid")],
)
def test_unhealthy_boot_fails_closed_without_known_good(tmp_path, mode, reason):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")

    result = supervisor.boot(FakeLauncher({"v1": mode}))

    assert result.status == "failed"
    assert result.fallback_used is False
    assert reason in result.reason


def test_health_timeout_stops_process(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root, timeout=0.02)
    supervisor.register_current_version("v1")
    launcher = FakeLauncher({"v1": "silent"})

    result = supervisor.boot(launcher)

    assert result.status == "failed"
    assert result.reason == "health timeout"
    assert launcher.processes[0].terminated is True


def test_unhealthy_active_restores_and_launches_known_good_once(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "good")
    supervisor = _supervisor(root)
    supervisor.register_current_version("good")
    first = supervisor.boot(FakeLauncher({"good": "healthy"}))
    assert first.status == "healthy"

    _active_state(root, "bad")
    supervisor.register_current_version("bad")
    launcher = FakeLauncher({"bad": "crash", "good": "healthy"})
    result = supervisor.boot(launcher)

    assert result.status == "healthy"
    assert result.fallback_used is True
    assert launcher.calls == ["bad", "good"]
    assert supervisor.active_version() == "good"
    assert json.loads((root / "state" / "policy.json").read_text(encoding="utf-8"))[
        "marker"
    ] == "good"


def test_tampered_known_good_version_blocks_before_launch(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")
    assert supervisor.boot(FakeLauncher()).status == "healthy"
    (root / "versions" / "v1" / "state" / "policy.json").write_text(
        json.dumps({"marker": "tampered", "rules": []}), encoding="utf-8"
    )
    launcher = FakeLauncher()

    result = supervisor.boot(launcher)

    assert result.status == "blocked"
    assert "known-good version integrity failed" in result.reason
    assert launcher.calls == []


def test_manual_recovery_restores_requested_version_and_logs(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")
    _active_state(root, "v2")
    supervisor.register_current_version("v2")

    supervisor.manual_recover("v1", "owner requested recovery")

    assert supervisor.active_version() == "v1"
    assert (root / "capabilities" / "marker.txt").read_text(encoding="utf-8") == "v1"
    event_types = {
        json.loads(path.read_text(encoding="utf-8"))["event_type"]
        for path in (root / "recovery" / "supervisor_logs").glob("*.json")
    }
    assert "manual_recovery" in event_types


def test_restore_failure_recovers_previous_active_state(tmp_path, monkeypatch):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")
    _active_state(root, "v2")
    supervisor.register_current_version("v2")
    original = supervisor_module._replace_tree
    calls = 0

    def fail_once(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated capabilities restore failure")
        original(source, target)

    monkeypatch.setattr(supervisor_module, "_replace_tree", fail_once)

    with pytest.raises(SupervisorError, match="previous active state restored"):
        supervisor.manual_recover("v1", "test transaction")

    assert supervisor.active_version() == "v2"
    assert json.loads((root / "state" / "policy.json").read_text(encoding="utf-8"))[
        "marker"
    ] == "v2"
    assert (root / "capabilities" / "marker.txt").read_text(encoding="utf-8") == "v2"


def test_register_refuses_to_replace_different_existing_version(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "first")
    supervisor = _supervisor(root)
    supervisor.register_current_version("same-id")
    _active_state(root, "different")

    with pytest.raises(VersionIntegrityError, match="existing version differs"):
        supervisor.register_current_version("same-id")


def test_health_signal_rejects_path_outside_recovery_root(tmp_path, monkeypatch):
    root = tmp_path / "seed"
    monkeypatch.setenv("SEED_SUPERVISED", "1")
    monkeypatch.setenv("SEED_BOOT_VERSION", "v1")
    monkeypatch.setenv("SEED_HEALTH_TOKEN", "secret")
    monkeypatch.setenv("SEED_HEALTH_FILE", str(tmp_path / "outside.json"))

    with pytest.raises(SupervisorError, match="outside recovery root"):
        emit_health_signal_from_env(root)

    assert not (tmp_path / "outside.json").exists()


def test_subprocess_probe_uses_supervisor_root_and_emits_real_health(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root, timeout=5)
    supervisor.register_current_version("v1")
    probe = Path(__file__).resolve().parents[1] / "scripts" / "supervisor_probe.py"
    launcher = SubprocessRuntimeLauncher(
        [sys.executable, str(probe), "--mode", "healthy"],
        seed_root=root,
    )

    result = supervisor.boot(launcher)
    BootSupervisor._stop(result.process)

    assert result.status == "healthy"
    assert result.reason == "health signal verified"
    assert supervisor.known_good().version_id == "v1"


def test_seed_data_root_override_is_shared_with_core(tmp_path, monkeypatch):
    root = tmp_path / "isolated-seed"
    monkeypatch.setenv("SEED_DATA_ROOT", str(root))

    assert forbidden.seed_data_dir() == root


def test_log_files_are_append_only_events(tmp_path):
    root = tmp_path / "seed"
    _active_state(root, "v1")
    supervisor = _supervisor(root)
    supervisor.register_current_version("v1")
    supervisor.boot(FakeLauncher())
    logs = sorted((root / "recovery" / "supervisor_logs").glob("*.json"))

    assert len(logs) >= 3
    assert len({path.name for path in logs}) == len(logs)
    assert all(
        json.loads(path.read_text(encoding="utf-8"))["schema_version"]
        == "seed.supervisor-event.v1"
        for path in logs
    )


def test_cli_reports_root_initialization_failure_without_traceback(tmp_path, capsys):
    invalid_root = tmp_path / "not-a-directory"
    invalid_root.write_text("occupied", encoding="utf-8")

    exit_code = supervisor_cli.main(
        ["--root", str(invalid_root), "--register-current", "v1"]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["status"] == "failed"
    assert output["error"]
