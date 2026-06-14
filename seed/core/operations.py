"""Transactional local operations: backup, restore, migrations, update staging."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path
from collections.abc import Callable


class OperationsError(RuntimeError):
    pass


class OperationsManager:
    def __init__(self, data_root: Path):
        self.root = Path(data_root).resolve()
        self.backups = self.root / "operations" / "backups"
        self.updates = self.root / "operations" / "updates"
        self.backups.mkdir(parents=True, exist_ok=True)
        self.updates.mkdir(parents=True, exist_ok=True)

    def create_backup(self, label: str = "manual") -> Path:
        target = self.backups / f"{int(time.time())}-{_safe(label)}"
        temp = Path(tempfile.mkdtemp(prefix=".backup-", dir=self.backups))
        try:
            for name in ("state", "capabilities", "active", "lineage", "data"):
                source = self.root / name
                if source.is_dir():
                    shutil.copytree(source, temp / name)
            manifest = {"schema_version": "seed.backup.v1", "created_at": time.time(),
                        "files": _hashes(temp)}
            (temp / "BACKUP.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            temp.replace(target)
            return target
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    def verify_backup(self, backup: Path) -> bool:
        backup = Path(backup).resolve()
        if self.backups not in backup.parents:
            raise OperationsError("backup outside managed root")
        manifest = json.loads((backup / "BACKUP.json").read_text(encoding="utf-8"))
        expected = manifest.get("files", {})
        return expected == _hashes(backup, exclude={"BACKUP.json"})

    def restore_backup(self, backup: Path, *, owner_confirmed: bool) -> None:
        if not owner_confirmed:
            raise OperationsError("owner confirmation required")
        if not self.verify_backup(backup):
            raise OperationsError("backup integrity failed")
        rollback = self.create_backup("pre-restore")
        try:
            for name in ("state", "capabilities", "active", "lineage", "data"):
                source = Path(backup) / name
                target = self.root / name
                if source.is_dir():
                    _replace_tree(source, target)
        except Exception as exc:
            for name in ("state", "capabilities", "active", "lineage", "data"):
                source = rollback / name
                if source.is_dir():
                    _replace_tree(source, self.root / name)
            raise OperationsError(f"restore failed and rolled back: {exc}") from exc

    def stage_update(self, package: Path, expected_sha256: str) -> Path:
        package = Path(package).resolve()
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        if digest != expected_sha256:
            raise OperationsError("update digest mismatch")
        target = self.updates / f"{digest}{package.suffix}"
        shutil.copy2(package, target)
        return target

    def schedule_update(self, staged_package: Path, *, owner_confirmed: bool) -> Path:
        if not owner_confirmed:
            raise OperationsError("owner confirmation required")
        staged = Path(staged_package).resolve()
        if self.updates not in staged.parents or not staged.is_file():
            raise OperationsError("update package is not staged")
        marker = self.updates / "pending_update.json"
        marker.write_text(json.dumps({
            "schema_version": "seed.pending-update.v1",
            "package": staged.name,
            "sha256": hashlib.sha256(staged.read_bytes()).hexdigest(),
            "scheduled_at": time.time(),
            "apply_on_next_supervised_boot": True,
        }, indent=2), encoding="utf-8")
        return marker

    def apply_migrations(self, migrations: dict[int, Callable[[Path], None]], *,
                         target_version: int, owner_confirmed: bool) -> int:
        if not owner_confirmed:
            raise OperationsError("owner confirmation required")
        state_file = self.root / "operations" / "migration_state.json"
        current = 0
        if state_file.is_file():
            current = int(json.loads(state_file.read_text(encoding="utf-8")).get("version", 0))
        if target_version < current:
            raise OperationsError("migration downgrade is not supported")
        backup = self.create_backup(f"pre-migration-{current}-to-{target_version}")
        try:
            for version in range(current + 1, target_version + 1):
                migration = migrations.get(version)
                if migration is None:
                    raise OperationsError(f"missing migration {version}")
                migration(self.root)
                state_file.write_text(json.dumps({
                    "schema_version": "seed.migration-state.v1",
                    "version": version, "updated_at": time.time(),
                }, indent=2), encoding="utf-8")
            return target_version
        except Exception as exc:
            self.restore_backup(backup, owner_confirmed=True)
            raise OperationsError(f"migration failed and rolled back: {exc}") from exc

    def uninstall_plan(self, *, remove_personal_data: bool = False) -> dict:
        paths = [str(self.root / "operations"), str(self.root / "recovery")]
        if remove_personal_data:
            paths.append(str(self.root))
        return {"schema_version": "seed.uninstall-plan.v1",
                "requires_owner_confirmation": True, "paths": paths,
                "remove_personal_data": remove_personal_data}

    def execute_uninstall(self, plan: dict, *, owner_confirmed: bool) -> int:
        if not owner_confirmed:
            raise OperationsError("owner confirmation required")
        if plan.get("schema_version") != "seed.uninstall-plan.v1":
            raise OperationsError("invalid uninstall plan")
        removed = 0
        for raw in plan.get("paths", []):
            path = Path(raw).resolve()
            if path != self.root and self.root not in path.parents:
                raise OperationsError("uninstall path outside data root")
            if path.exists():
                shutil.rmtree(path)
                removed += 1
        return removed


def _safe(value: str) -> str:
    out = "".join(ch for ch in value if ch.isalnum() or ch in "._-")[:48]
    if not out:
        raise OperationsError("invalid label")
    return out


def _hashes(root: Path, exclude: set[str] | None = None) -> dict[str, str]:
    exclude = exclude or set()
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file() and path.name not in exclude
    }


def _replace_tree(source: Path, target: Path) -> None:
    temp = target.with_name(f".{target.name}.new")
    shutil.rmtree(temp, ignore_errors=True)
    shutil.copytree(source, temp)
    shutil.rmtree(target, ignore_errors=True)
    temp.replace(target)
