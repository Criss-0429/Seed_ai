"""Independent stable boot, health-check, fallback, and recovery boundary."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from .core.lineage import LineageIntegrityError, LineageStore


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REQUIRED_STATE_FILES = ("policy.json", "ui_manifest.json", "user_model.json")


class SupervisorError(RuntimeError):
    """Raised when boot or recovery cannot proceed safely."""


class VersionIntegrityError(SupervisorError):
    """Raised when a version or pointer fails validation."""


@dataclass(frozen=True)
class SupervisorPolicy:
    health_timeout_seconds: float = 30.0
    poll_interval_seconds: float = 0.1

    def validate(self) -> None:
        if self.health_timeout_seconds <= 0:
            raise SupervisorError("health timeout must be positive")
        if self.poll_interval_seconds <= 0:
            raise SupervisorError("poll interval must be positive")


@dataclass(frozen=True)
class KnownGoodRecord:
    schema_version: str
    version_id: str
    version_digest: str
    verified_at: str
    source_boot_id: str

    def validate(self) -> None:
        if self.schema_version != "seed.known-good.v1":
            raise VersionIntegrityError("unsupported known-good schema")
        _safe_component(self.version_id, "known-good version_id")
        if not re.fullmatch(r"[0-9a-f]{64}", self.version_digest):
            raise VersionIntegrityError("known-good version digest invalid")
        if not self.verified_at or not self.source_boot_id:
            raise VersionIntegrityError("known-good record incomplete")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class BootResult:
    schema_version: str
    boot_id: str
    requested_version: str
    launched_version: str
    status: str
    fallback_used: bool
    reason: str
    process: Any = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "boot_id": self.boot_id,
            "requested_version": self.requested_version,
            "launched_version": self.launched_version,
            "status": self.status,
            "fallback_used": self.fallback_used,
            "reason": self.reason,
        }


class ProcessHandle(Protocol):
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def wait(self, timeout: float | None = None) -> int: ...


Launcher = Callable[[str, Path, str], ProcessHandle]


class SubprocessRuntimeLauncher:
    """Launch the immutable runtime command with supervised health env."""

    def __init__(
        self,
        command: list[str],
        *,
        seed_root: Path,
        env: dict[str, str] | None = None,
    ):
        if not command or not all(isinstance(part, str) and part for part in command):
            raise SupervisorError("runtime command is required")
        self.command = list(command)
        self.seed_root = Path(seed_root).resolve()
        self.env = dict(env or {})

    def __call__(self, version_id: str, health_file: Path, token: str) -> ProcessHandle:
        env = os.environ.copy()
        env.update(self.env)
        env.update({
            "SEED_SUPERVISED": "1",
            "SEED_BOOT_VERSION": version_id,
            "SEED_DATA_ROOT": str(self.seed_root),
            "SEED_HEALTH_FILE": str(health_file),
            "SEED_HEALTH_TOKEN": token,
        })
        return subprocess.Popen(self.command, env=env)  # noqa: S603


class BootSupervisor:
    """Stable external authority over state-based runtime boot and recovery."""

    def __init__(self, root: Path, policy: SupervisorPolicy | None = None):
        self.root = Path(root).expanduser().resolve()
        self.policy = policy or SupervisorPolicy()
        self.policy.validate()
        self.active_root = self.root / "active"
        self.state_dir = self.root / "state"
        self.capabilities_dir = self.root / "capabilities"
        self.versions_dir = self.root / "versions"
        self.lineage_root = self.root / "lineage"
        self.recovery_root = self.root / "recovery"
        self.health_root = self.recovery_root / "health"
        self.logs_root = self.recovery_root / "supervisor_logs"
        self.known_good_path = self.recovery_root / "known_good.json"
        self.active_root.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.health_root.mkdir(parents=True, exist_ok=True)
        self.logs_root.mkdir(parents=True, exist_ok=True)

    def register_current_version(self, version_id: str) -> Path:
        """Explicitly snapshot current state as the first recoverable version."""
        _safe_component(version_id, "version_id")
        self._validate_active_state()
        target = self.versions_dir / version_id
        temp = Path(tempfile.mkdtemp(prefix=".register-", dir=self.versions_dir))
        try:
            shutil.copytree(self.state_dir, temp / "state")
            if self.capabilities_dir.is_dir():
                shutil.copytree(self.capabilities_dir, temp / "capabilities")
            else:
                (temp / "capabilities").mkdir()
            if target.exists():
                if _tree_hashes(target) != _tree_hashes(temp):
                    raise VersionIntegrityError(f"existing version differs: {version_id}")
            else:
                temp.replace(target)
            self.validate_version(version_id)
            self._write_active_pointer(version_id, version_id)
            self._log("version_registered", {"version_id": version_id})
            return target
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    def validate_version(self, version_id: str) -> Path:
        _safe_component(version_id, "version_id")
        version = self.versions_dir / version_id
        state = version / "state"
        if not state.is_dir():
            raise VersionIntegrityError(f"version state missing: {version_id}")
        for name in _REQUIRED_STATE_FILES:
            _read_json_object(state / name, f"version {version_id}/{name}")
        capabilities = version / "capabilities"
        if not capabilities.is_dir():
            raise VersionIntegrityError(f"version capabilities missing: {version_id}")
        return version

    def active_version(self) -> str:
        pointer = _read_json_object(
            self.active_root / "current_version.json", "active pointer"
        )
        if pointer.get("schema_version") != "seed.active-version.v1":
            raise VersionIntegrityError("unsupported active pointer schema")
        version_id = str(pointer.get("version_id") or "")
        _safe_component(version_id, "active version_id")
        self.validate_version(version_id)
        return version_id

    def known_good(self) -> KnownGoodRecord | None:
        if not self.known_good_path.is_file():
            return None
        raw = _read_json_object(self.known_good_path, "known-good record")
        try:
            record = KnownGoodRecord(**raw)
        except TypeError as exc:
            raise VersionIntegrityError("invalid known-good record") from exc
        record.validate()
        version = self.validate_version(record.version_id)
        if _tree_digest(version) != record.version_digest:
            raise VersionIntegrityError("known-good version integrity failed")
        return record

    def boot(self, launcher: Launcher) -> BootResult:
        boot_id = str(uuid.uuid4())
        try:
            requested = self.active_version()
            self._verify_lineage()
            if self.known_good_path.is_file():
                self.known_good()
        except Exception as exc:
            self._log("boot_blocked", {"boot_id": boot_id, "reason": str(exc)})
            return BootResult(
                "seed.boot-result.v1", boot_id, "", "", "blocked", False, str(exc)
            )

        self._log("boot_started", {"boot_id": boot_id, "version_id": requested})
        healthy, reason, process = self._launch_and_wait(
            launcher, requested, boot_id, attempt="active"
        )
        if healthy:
            self._mark_known_good(requested, boot_id)
            self._log("boot_healthy", {"boot_id": boot_id, "version_id": requested})
            return BootResult(
                "seed.boot-result.v1", boot_id, requested, requested,
                "healthy", False, reason, process,
            )

        self._stop(process)
        self._log("boot_unhealthy", {
            "boot_id": boot_id, "version_id": requested, "reason": reason,
        })
        try:
            known_good = self.known_good()
        except Exception as exc:
            known_good = None
            reason = f"{reason}; known-good invalid: {exc}"
        if known_good is None or known_good.version_id == requested:
            self._log("fallback_blocked", {"boot_id": boot_id, "reason": reason})
            return BootResult(
                "seed.boot-result.v1", boot_id, requested, requested,
                "failed", False, reason,
            )

        try:
            self.restore_version(
                known_good.version_id,
                reason=f"automatic fallback after unhealthy boot {boot_id}",
                event_type="fallback_restored",
            )
        except Exception as exc:
            fallback_reason = f"{reason}; fallback restore failed: {exc}"
            self._log("fallback_failed", {"boot_id": boot_id, "reason": fallback_reason})
            return BootResult(
                "seed.boot-result.v1", boot_id, requested, "", "failed", True,
                fallback_reason,
            )

        healthy, fallback_reason, fallback_process = self._launch_and_wait(
            launcher, known_good.version_id, boot_id, attempt="fallback"
        )
        if healthy:
            self._mark_known_good(known_good.version_id, boot_id)
            self._log("fallback_healthy", {
                "boot_id": boot_id,
                "requested_version": requested,
                "version_id": known_good.version_id,
            })
            return BootResult(
                "seed.boot-result.v1", boot_id, requested, known_good.version_id,
                "healthy", True, fallback_reason, fallback_process,
            )
        self._stop(fallback_process)
        final_reason = f"active unhealthy: {reason}; fallback unhealthy: {fallback_reason}"
        self._log("fallback_unhealthy", {"boot_id": boot_id, "reason": final_reason})
        return BootResult(
            "seed.boot-result.v1", boot_id, requested, known_good.version_id,
            "failed", True, final_reason,
        )

    def apply_pending_update(self, runtime_path: Path) -> dict | None:
        """Applica un update staged da OperationsManager PRIMA del boot.

        Il pacchetto vive sotto `operations/updates/<name>`; il marker
        `pending_update.json` dichiara nome + sha256. Verifica l'hash, fa il
        backup del runtime corrente, sostituisce il binario e consuma il marker.
        Fail-closed: su qualunque errore il runtime resta intatto e il boot
        prosegue con la versione corrente."""
        runtime_path = Path(runtime_path)
        updates_dir = self.root / "operations" / "updates"
        marker = updates_dir / "pending_update.json"
        if not marker.is_file():
            return None
        try:
            data = _read_json_object(marker, "pending update marker")
            if not data.get("apply_on_next_supervised_boot"):
                return None
            package = updates_dir / str(data.get("package") or "")
            expected = str(data.get("sha256") or "")
            if not package.is_file():
                raise SupervisorError("staged update package missing")
            digest = hashlib.sha256(package.read_bytes()).hexdigest()
            if digest != expected or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise SupervisorError("staged update digest mismatch")
            if not runtime_path.is_file():
                raise SupervisorError("runtime target missing")
            backups = self.recovery_root / "runtime_backups"
            backups.mkdir(parents=True, exist_ok=True)
            if package.suffix.lower() == ".zip":
                runtime_dir = runtime_path.parent.resolve()
                backup = backups / f"{time.time_ns()}-{runtime_dir.name}"
                shutil.copytree(runtime_dir, backup)
                temp = runtime_dir.with_name(f".{runtime_dir.name}.update-staging")
                shutil.rmtree(temp, ignore_errors=True)
                temp.mkdir(parents=True)
                _safe_extract_zip(package, temp)
                if not (temp / runtime_path.name).is_file():
                    raise SupervisorError("updated runtime executable missing")
                _replace_tree(temp, runtime_dir)
                shutil.rmtree(temp, ignore_errors=True)
                kind = "runtime-directory"
            else:
                backup = backups / f"{time.time_ns()}-{runtime_path.name}"
                shutil.copy2(runtime_path, backup)
                temp = runtime_path.with_suffix(runtime_path.suffix + ".update-staging")
                shutil.copy2(package, temp)
                temp.replace(runtime_path)
                kind = "runtime-file"
            applied = updates_dir / "applied"
            applied.mkdir(parents=True, exist_ok=True)
            marker.replace(applied / f"{time.time_ns()}-pending_update.json")
            self._log("update_applied", {
                "version": data.get("sha256"), "runtime": runtime_path.name,
                "backup": backup.name})
            return {"applied": True, "runtime": str(runtime_path),
                    "backup": str(backup), "kind": kind}
        except (OSError, SupervisorError, ValueError) as exc:
            self._log("update_apply_failed", {"reason": str(exc)})
            failed = updates_dir / "failed"
            failed.mkdir(parents=True, exist_ok=True)
            if marker.is_file():
                marker.replace(failed / f"{time.time_ns()}-pending_update.json")
            return {"applied": False, "reason": str(exc)}

    def rollback_runtime_update(self, update: dict) -> dict:
        """Ripristina backup runtime creato da ``apply_pending_update``."""
        if not update.get("applied"):
            raise SupervisorError("cannot rollback unapplied update")
        runtime = Path(str(update.get("runtime") or "")).resolve()
        backup = Path(str(update.get("backup") or "")).resolve()
        backups = (self.recovery_root / "runtime_backups").resolve()
        if backups not in backup.parents or not backup.exists():
            raise SupervisorError("runtime update backup invalid")
        if update.get("kind") == "runtime-directory":
            _replace_tree(backup, runtime.parent)
        else:
            shutil.copy2(backup, runtime)
        self._log("update_rolled_back", {
            "runtime": runtime.name, "backup": backup.name,
        })
        return {"rolled_back": True, "runtime": str(runtime)}

    def manual_recover(self, version_id: str, reason: str) -> str:
        if not isinstance(reason, str) or not reason.strip():
            raise SupervisorError("manual recovery reason is required")
        self.restore_version(version_id, reason=reason, event_type="manual_recovery")
        return version_id

    def restore_version(self, version_id: str, *, reason: str, event_type: str) -> None:
        version = self.validate_version(version_id)
        backup = Path(tempfile.mkdtemp(prefix=".restore-backup-", dir=self.recovery_root))
        try:
            if self.state_dir.is_dir():
                shutil.copytree(self.state_dir, backup / "state")
            if self.capabilities_dir.is_dir():
                shutil.copytree(self.capabilities_dir, backup / "capabilities")
            pointer = self.active_root / "current_version.json"
            if pointer.is_file():
                shutil.copy2(pointer, backup / "current_version.json")
            _replace_tree(version / "state", self.state_dir)
            _replace_tree(version / "capabilities", self.capabilities_dir)
            self._write_active_pointer(version_id, version_id)
            self._validate_active_state()
            self._log(event_type, {"version_id": version_id, "reason": reason})
        except Exception as exc:
            self._restore_backup(backup)
            raise SupervisorError(f"restore failed; previous active state restored: {exc}") from exc
        finally:
            shutil.rmtree(backup, ignore_errors=True)

    def _launch_and_wait(
        self, launcher: Launcher, version_id: str, boot_id: str, *, attempt: str
    ) -> tuple[bool, str, ProcessHandle | None]:
        token = secrets.token_urlsafe(32)
        health_file = self.health_root / f"{boot_id}-{attempt}.json"
        health_file.unlink(missing_ok=True)
        try:
            process = launcher(version_id, health_file, token)
        except Exception as exc:
            return False, f"launch failed: {exc}", None
        deadline = time.monotonic() + self.policy.health_timeout_seconds
        while time.monotonic() < deadline:
            if health_file.is_file():
                try:
                    signal = _read_json_object(health_file, "health signal")
                    if (
                        signal.get("schema_version") == "seed.health-signal.v1"
                        and signal.get("version_id") == version_id
                        and signal.get("token_sha256") == _token_digest(token)
                    ):
                        return True, "health signal verified", process
                    return False, "health signal invalid", process
                finally:
                    health_file.unlink(missing_ok=True)
            exit_code = process.poll()
            if exit_code is not None:
                return False, f"process exited before health: {exit_code}", process
            time.sleep(self.policy.poll_interval_seconds)
        return False, "health timeout", process

    def _mark_known_good(self, version_id: str, boot_id: str) -> None:
        self.validate_version(version_id)
        record = KnownGoodRecord(
            "seed.known-good.v1",
            version_id,
            _tree_digest(self.validate_version(version_id)),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            boot_id,
        )
        _atomic_replace_json(self.known_good_path, record.to_dict())

    def _verify_lineage(self) -> None:
        if not self.lineage_root.exists():
            return
        try:
            LineageStore(self.lineage_root).verify_integrity()
        except LineageIntegrityError as exc:
            raise VersionIntegrityError(f"lineage integrity failed: {exc}") from exc

    def _validate_active_state(self) -> None:
        if not self.state_dir.is_dir():
            raise VersionIntegrityError("active state missing")
        for name in _REQUIRED_STATE_FILES:
            _read_json_object(self.state_dir / name, f"active state/{name}")

    def _write_active_pointer(self, version_id: str, rollback_version: str) -> None:
        _safe_component(version_id, "active version_id")
        _safe_component(rollback_version, "rollback version_id")
        _atomic_replace_json(
            self.active_root / "current_version.json",
            {
                "schema_version": "seed.active-version.v1",
                "version_id": version_id,
                "rollback_version": rollback_version,
            },
        )

    def _restore_backup(self, backup: Path) -> None:
        _replace_tree(backup / "state", self.state_dir)
        _replace_tree(backup / "capabilities", self.capabilities_dir)
        pointer = self.active_root / "current_version.json"
        backup_pointer = backup / "current_version.json"
        if backup_pointer.is_file():
            shutil.copy2(backup_pointer, pointer)
        else:
            pointer.unlink(missing_ok=True)

    def _log(self, event_type: str, payload: dict[str, Any]) -> Path:
        event = {
            "schema_version": "seed.supervisor-event.v1",
            "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event_type": event_type,
            "payload": payload,
        }
        path = self.logs_root / f"{time.time_ns()}-{event['event_id']}.json"
        _atomic_create_json(path, event)
        return path

    @staticmethod
    def _stop(process: ProcessHandle | None) -> None:
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            pass


def emit_health_signal_from_env(root: Path) -> bool:
    """Emit health only when launched by the external supervisor."""
    if os.environ.get("SEED_SUPERVISED") != "1":
        return False
    health_file = Path(os.environ.get("SEED_HEALTH_FILE", ""))
    token = os.environ.get("SEED_HEALTH_TOKEN", "")
    version_id = os.environ.get("SEED_BOOT_VERSION", "")
    if not token:
        raise SupervisorError("supervised health token missing")
    _safe_component(version_id, "boot version_id")
    allowed = (Path(root) / "recovery" / "health").resolve()
    try:
        health_file.resolve().relative_to(allowed)
    except ValueError as exc:
        raise SupervisorError("health file outside recovery root") from exc
    _atomic_replace_json(
        health_file,
        {
            "schema_version": "seed.health-signal.v1",
            "version_id": version_id,
            "token_sha256": _token_digest(token),
        },
    )
    return True


def default_seed_root() -> Path:
    override = os.environ.get("SEED_DATA_ROOT")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(base) / "SEED"
    return Path.home() / ".seed"


def _safe_component(value: str, field_name: str) -> None:
    if not _SAFE_COMPONENT.fullmatch(value):
        raise VersionIntegrityError(f"unsafe {field_name}: {value!r}")


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise VersionIntegrityError(f"{label} missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VersionIntegrityError(f"{label} invalid") from exc
    if not isinstance(data, dict):
        raise VersionIntegrityError(f"{label} must be an object")
    return data


def _replace_tree(source: Path, target: Path) -> None:
    staging = target.parent / f".{target.name}.supervisor-staging"
    shutil.rmtree(staging, ignore_errors=True)
    if source.is_dir():
        shutil.copytree(source, staging)
    else:
        staging.mkdir(parents=True)
    shutil.rmtree(target, ignore_errors=True)
    staging.replace(target)


def _tree_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def _tree_digest(root: Path) -> str:
    canonical = json.dumps(
        _tree_hashes(root), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_extract_zip(package: Path, target: Path) -> None:
    with zipfile.ZipFile(package) as archive:
        root = target.resolve()
        for info in archive.infolist():
            destination = (target / info.filename).resolve()
            try:
                destination.relative_to(root)
            except ValueError as exc:
                raise SupervisorError("update ZIP contains unsafe path") from exc
        archive.extractall(target)


def _atomic_create_json(path: Path, data: dict[str, Any]) -> None:
    if path.exists():
        raise SupervisorError(f"append-only file already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        temp = Path(handle.name)
    try:
        if path.exists():
            raise SupervisorError(f"append-only file already exists: {path.name}")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _atomic_replace_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        temp = Path(handle.name)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
