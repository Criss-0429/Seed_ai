"""Updater reale: il supervisor applica un update staged prima del boot,
verifica lo sha256, fa backup del runtime e consuma il marker (fail-closed)."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.supervisor import BootSupervisor  # noqa: E402


def _stage(root: Path, runtime_bytes: bytes, pkg_bytes: bytes, sha: str | None = None):
    runtime = root / "SEED.exe"
    runtime.write_bytes(runtime_bytes)
    updates = root / "operations" / "updates"
    updates.mkdir(parents=True, exist_ok=True)
    pkg = updates / "update-pkg.exe"
    pkg.write_bytes(pkg_bytes)
    digest = sha if sha is not None else hashlib.sha256(pkg_bytes).hexdigest()
    (updates / "pending_update.json").write_text(json.dumps({
        "schema_version": "seed.pending-update.v1", "package": pkg.name,
        "sha256": digest, "apply_on_next_supervised_boot": True,
    }), encoding="utf-8")
    return runtime, updates


def test_no_marker_returns_none(tmp_path):
    sup = BootSupervisor(tmp_path)
    assert sup.apply_pending_update(tmp_path / "SEED.exe") is None


def test_valid_update_is_applied_with_backup(tmp_path):
    sup = BootSupervisor(tmp_path)
    runtime, updates = _stage(tmp_path, b"OLD-RUNTIME", b"NEW-RUNTIME")
    result = sup.apply_pending_update(runtime)
    assert result["applied"] is True
    assert runtime.read_bytes() == b"NEW-RUNTIME"          # binario sostituito
    backups = list((tmp_path / "recovery" / "runtime_backups").glob("*"))
    assert backups and backups[0].read_bytes() == b"OLD-RUNTIME"   # backup runtime
    assert not (updates / "pending_update.json").exists()  # marker consumato
    assert list((updates / "applied").glob("*pending_update.json"))


def test_digest_mismatch_leaves_runtime_intact(tmp_path):
    sup = BootSupervisor(tmp_path)
    runtime, updates = _stage(tmp_path, b"OLD", b"NEW", sha="0" * 64)
    result = sup.apply_pending_update(runtime)
    assert result["applied"] is False
    assert runtime.read_bytes() == b"OLD"                  # fail-closed
    assert list((updates / "failed").glob("*pending_update.json"))


def test_missing_package_fails_closed(tmp_path):
    sup = BootSupervisor(tmp_path)
    runtime = tmp_path / "SEED.exe"
    runtime.write_bytes(b"OLD")
    updates = tmp_path / "operations" / "updates"
    updates.mkdir(parents=True)
    (updates / "pending_update.json").write_text(json.dumps({
        "package": "ghost.exe", "sha256": "a" * 64,
        "apply_on_next_supervised_boot": True}), encoding="utf-8")
    result = sup.apply_pending_update(runtime)
    assert result["applied"] is False and runtime.read_bytes() == b"OLD"


def test_onedir_zip_update_and_explicit_runtime_rollback(tmp_path):
    sup = BootSupervisor(tmp_path / "data")
    runtime_dir = tmp_path / "install" / "runtime"
    runtime_dir.mkdir(parents=True)
    runtime = runtime_dir / "SEED.exe"
    runtime.write_bytes(b"OLD")
    (runtime_dir / "old.dll").write_bytes(b"OLD-DLL")
    updates = sup.root / "operations" / "updates"
    updates.mkdir(parents=True)
    package = updates / "runtime.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("SEED.exe", b"NEW")
        archive.writestr("new.dll", b"NEW-DLL")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (updates / "pending_update.json").write_text(json.dumps({
        "schema_version": "seed.pending-update.v1", "package": package.name,
        "sha256": digest, "apply_on_next_supervised_boot": True,
    }), encoding="utf-8")

    result = sup.apply_pending_update(runtime)

    assert result["applied"] is True
    assert result["kind"] == "runtime-directory"
    assert runtime.read_bytes() == b"NEW"
    assert not (runtime_dir / "old.dll").exists()
    assert (runtime_dir / "new.dll").is_file()

    rollback = sup.rollback_runtime_update(result)

    assert rollback["rolled_back"] is True
    assert runtime.read_bytes() == b"OLD"
    assert (runtime_dir / "old.dll").is_file()
    assert not (runtime_dir / "new.dll").exists()


def test_onedir_zip_path_traversal_is_blocked(tmp_path):
    sup = BootSupervisor(tmp_path / "data")
    runtime_dir = tmp_path / "install" / "runtime"
    runtime_dir.mkdir(parents=True)
    runtime = runtime_dir / "SEED.exe"
    runtime.write_bytes(b"OLD")
    updates = sup.root / "operations" / "updates"
    updates.mkdir(parents=True)
    package = updates / "runtime.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("../escape.exe", b"BAD")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (updates / "pending_update.json").write_text(json.dumps({
        "package": package.name, "sha256": digest,
        "apply_on_next_supervised_boot": True,
    }), encoding="utf-8")

    result = sup.apply_pending_update(runtime)

    assert result["applied"] is False
    assert runtime.read_bytes() == b"OLD"
    assert not (tmp_path / "escape.exe").exists()
