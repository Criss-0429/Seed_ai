"""Retention dati locali: tiene i piu' recenti, cancella il resto, rispetta i
limiti e l'opt-out. Usa SEED_DATA_ROOT su tmp_path: niente dati reali toccati."""

from __future__ import annotations

import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden  # noqa: E402
from seed.core.config import MaintenanceConfig  # noqa: E402
from seed.core.lineage import LineageStore, MutationCandidate  # noqa: E402
from seed.core.maintenance import prune_runtime_data  # noqa: E402
from seed.supervisor import BootSupervisor  # noqa: E402


def _mkdirs(parent: Path, n: int, *, stagger=True):
    parent.mkdir(parents=True, exist_ok=True)
    made = []
    for i in range(n):
        d = parent / f"v{i:03d}"
        d.mkdir()
        (d / "x").write_text("x", encoding="utf-8")
        if stagger:
            import os
            t = time.time() - (n - i) * 10   # i piu' alti = piu' recenti
            os.utime(d, (t, t))
        made.append(d)
    return made


def test_keeps_recent_versions_and_prunes_rest(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    root = forbidden.seed_data_dir()
    _mkdirs(root / "versions", 15)
    res = prune_runtime_data(MaintenanceConfig(keep_versions=10, keep_backups=0,
                                               keep_lab_runs=0, trace_days=0))
    remaining = sorted(p.name for p in (root / "versions").iterdir())
    assert len(remaining) == 10
    assert "v014" in remaining and "v000" not in remaining   # tenuti i piu' recenti
    assert res["versions"] == 5


def test_disabled_does_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    root = forbidden.seed_data_dir()
    _mkdirs(root / "versions", 12)
    res = prune_runtime_data(MaintenanceConfig(enabled=False))
    assert res == {}
    assert len(list((root / "versions").iterdir())) == 12


def test_zero_keep_is_unlimited(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    root = forbidden.seed_data_dir()
    _mkdirs(root / "operations" / "backups", 8)
    prune_runtime_data(MaintenanceConfig(keep_backups=0, keep_versions=0,
                                         keep_lab_runs=0, trace_days=0))
    assert len(list((root / "operations" / "backups").iterdir())) == 8


def test_prunes_old_traces_by_age(tmp_path, monkeypatch):
    import os
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    root = forbidden.seed_data_dir()
    traces = root / "data" / "traces"
    traces.mkdir(parents=True)
    old = traces / "2020-01-01.jsonl"
    old.write_text("{}", encoding="utf-8")
    new = traces / "today.jsonl"
    new.write_text("{}", encoding="utf-8")
    os.utime(old, (time.time() - 60 * 86400,) * 2)
    res = prune_runtime_data(MaintenanceConfig(trace_days=30, keep_versions=0,
                                               keep_backups=0, keep_lab_runs=0))
    assert not old.exists() and new.exists()
    assert res["traces"] == 1


def _write_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _record_candidate(store: LineageStore, mutation_id: str, parent: str, status: str):
    candidate = MutationCandidate(
        mutation_id=mutation_id,
        parent_version=parent,
        reason="retention test",
        hypothesis="retention preserves reachable artifacts",
        target_scope=["state"],
        expected_signals=[],
        evaluation_plan=["offline"],
        rollback_plan="restore parent",
    )
    store.record_candidate(candidate)
    if status == "validating":
        candidate = store.transition(candidate, "built", reason="test")
        store.transition(candidate, "validating", reason="test")
    elif status != "proposed":
        store.transition(candidate, status, reason="test")


def test_protects_active_rollback_known_good_and_open_candidate_versions(
        tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    versions = tmp_path / "versions"
    _mkdirs(versions, 15)
    _write_json(tmp_path / "active/current_version.json", {
        "schema_version": "seed.active-version.v1",
        "version_id": "v000", "rollback_version": "v001"})
    _write_json(tmp_path / "recovery/known_good.json", {
        "schema_version": "seed.known-good.v1", "version_id": "v002"})
    _record_candidate(LineageStore(tmp_path / "lineage"), "v004", "v003", "validating")

    prune_runtime_data(MaintenanceConfig(
        keep_versions=3, keep_backups=0, keep_runtime_backups=0,
        keep_update_history=0, keep_lab_runs=0, trace_days=0))

    remaining = {path.name for path in versions.iterdir()}
    assert {"v000", "v001", "v002", "v003", "v004"} <= remaining


def test_manual_backups_survive_automatic_backup_retention(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    backups = tmp_path / "operations/backups"
    _mkdirs(backups, 0)
    for name in ("100-ui", "101-manual"):
        (backups / name).mkdir()
    for index in range(6):
        path = backups / f"{200 + index}-pre-migration-{index}"
        path.mkdir()
        import os
        os.utime(path, (time.time() + index,) * 2)

    prune_runtime_data(MaintenanceConfig(
        keep_versions=0, keep_backups=2, keep_runtime_backups=0,
        keep_update_history=0, keep_lab_runs=0, trace_days=0))

    names = {path.name for path in backups.iterdir()}
    assert {"100-ui", "101-manual"} <= names
    assert len([name for name in names if "pre-migration" in name]) == 2


def test_lab_prunes_only_terminal_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    store = LineageStore(tmp_path / "lineage")
    for mutation, status in (("open-one", "validating"),
                             ("done-old", "rejected"),
                             ("done-new", "archived")):
        _record_candidate(store, mutation, "base", status)
    descendants = tmp_path / "lab/descendants"
    runs = tmp_path / "lab/evaluator_runs"
    for index, mutation in enumerate(("open-one", "done-old", "done-new", "unknown")):
        (descendants / mutation).mkdir(parents=True, exist_ok=True)
        (runs / f"{mutation}.json").parent.mkdir(parents=True, exist_ok=True)
        (runs / f"{mutation}.json").write_text("{}", encoding="utf-8")
        import os
        stamp = time.time() + index
        os.utime(descendants / mutation, (stamp, stamp))
        os.utime(runs / f"{mutation}.json", (stamp, stamp))

    prune_runtime_data(MaintenanceConfig(
        keep_versions=0, keep_backups=0, keep_runtime_backups=0,
        keep_update_history=0, keep_lab_runs=1, trace_days=0))

    remaining_desc = {path.name for path in descendants.iterdir()}
    remaining_runs = {path.stem for path in runs.iterdir()}
    assert {"open-one", "done-new", "unknown"} == remaining_desc
    assert {"open-one", "done-new", "unknown"} == remaining_runs


def test_update_cache_keeps_pending_and_partial_but_removes_orphans(
        tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    updates = tmp_path / "operations/updates"
    updates.mkdir(parents=True)
    (updates / "pending.zip").write_bytes(b"pending")
    (updates / "orphan.zip").write_bytes(b"orphan")
    (updates / "downloads").mkdir()
    (updates / "downloads/resume.zip.part").write_bytes(b"partial")
    _write_json(updates / "pending_update.json", {"package": "pending.zip"})
    for timestamp in (100, 200, 300, 400):
        _write_json(
            updates / f"applied/{timestamp}-pending_update.json",
            {"package": f"old-{timestamp}.zip"},
        )

    result = prune_runtime_data(MaintenanceConfig(
        keep_versions=0, keep_backups=0, keep_runtime_backups=0,
        keep_update_history=1, keep_lab_runs=0, trace_days=0))

    assert (updates / "pending.zip").is_file()
    assert not (updates / "orphan.zip").exists()
    assert (updates / "downloads/resume.zip.part").is_file()
    assert len(list((updates / "applied").iterdir())) == 1
    assert result["update_packages"] == 1


def test_runtime_backup_retention_uses_supervisor_timestamp_not_copied_mtime(
        tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    backups = tmp_path / "recovery/runtime_backups"
    backups.mkdir(parents=True)
    old = backups / "100-runtime"
    fresh = backups / "200-runtime"
    manual = backups / "manual-recovery"
    for path in (old, fresh, manual):
        path.mkdir()
    import os
    os.utime(old, (time.time() + 100, time.time() + 100))
    os.utime(fresh, (time.time() - 100, time.time() - 100))

    prune_runtime_data(MaintenanceConfig(
        keep_versions=0, keep_backups=0, keep_runtime_backups=1,
        keep_update_history=0, keep_lab_runs=0, trace_days=0))

    assert not old.exists()
    assert fresh.exists()
    assert manual.exists()


def _stage_runtime_zip(supervisor: BootSupervisor, runtime: Path, payload: bytes):
    updates = supervisor.root / "operations/updates"
    updates.mkdir(parents=True, exist_ok=True)
    package = updates / f"{hashlib.sha256(payload).hexdigest()}.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("SEED.exe", payload)
        archive.writestr("same-dir.txt", payload)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    _write_json(updates / "pending_update.json", {
        "package": package.name, "sha256": digest,
        "apply_on_next_supervised_boot": True,
    })
    return supervisor.apply_pending_update(runtime)


def test_repeated_updates_replace_same_runtime_directory_and_bound_backups(
        tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    monkeypatch.setenv("SEED_DATA_ROOT", str(data_root))
    runtime_dir = tmp_path / "install/runtime"
    runtime_dir.mkdir(parents=True)
    runtime = runtime_dir / "SEED.exe"
    runtime.write_bytes(b"v0")
    supervisor = BootSupervisor(data_root)
    original_path = runtime.resolve()

    first = _stage_runtime_zip(supervisor, runtime, b"v1")
    second = _stage_runtime_zip(supervisor, runtime, b"v2")

    assert first["applied"] and second["applied"]
    assert runtime.resolve() == original_path
    assert runtime.read_bytes() == b"v2"
    assert not list(runtime_dir.parent.glob("runtime-v*"))
    prune_runtime_data(MaintenanceConfig(
        keep_versions=0, keep_backups=0, keep_runtime_backups=1,
        keep_update_history=1, keep_lab_runs=0, trace_days=0))
    assert len(list((data_root / "recovery/runtime_backups").iterdir())) == 1
