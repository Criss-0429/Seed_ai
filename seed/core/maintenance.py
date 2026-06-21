"""Reachability-aware retention for local, recoverable SEED artifacts."""

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from . import forbidden
from .config import MaintenanceConfig
from .lineage import LineageError, LineageStore

log = logging.getLogger("seed.maintenance")
_TERMINAL_CANDIDATE_STATES = {"archived", "rejected", "rolled_back"}
_AUTO_BACKUP = re.compile(r"^\d+-(?:pre-migration|pre-restore)(?:-|$)")
_TIMESTAMPED_ENTRY = re.compile(r"^(\d+)-")
_UPDATE_HISTORY = re.compile(r"^\d+-pending_update\.json$")


@dataclass(frozen=True)
class _LineageReachability:
    protected_versions: frozenset[str]
    protected_mutations: frozenset[str]
    terminal_mutations: frozenset[str]


def _remove(path: Path) -> bool:
    try:
        shutil.rmtree(path) if path.is_dir() else path.unlink()
        return True
    except OSError as exc:
        log.warning("retention: impossibile rimuovere %s (%s)", path, exc)
        return False


def _entries(parent: Path) -> list[Path]:
    if not parent.is_dir():
        return []
    entries = list(parent.iterdir())
    entries.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return entries


def _prune_keep_recent(
    parent: Path,
    keep: int,
    *,
    protected: set[str] | frozenset[str] = frozenset(),
    eligible=None,
    newest_key=None,
) -> int:
    """Keep a bounded number while never deleting protected/ineligible items."""
    if keep <= 0:
        return 0
    entries = _entries(parent)
    if newest_key is not None:
        entries.sort(key=newest_key, reverse=True)
    protected_count = sum(path.name in protected for path in entries)
    candidates = [
        path for path in entries
        if path.name not in protected and (eligible is None or eligible(path))
    ]
    keep_candidates = max(0, keep - protected_count) if eligible is None else keep
    return sum(_remove(path) for path in candidates[keep_candidates:])


def _timestamp_prefix(path: Path) -> int:
    match = _TIMESTAMPED_ENTRY.match(path.name)
    return int(match.group(1)) if match else -1


def _prune_old_files(parent: Path, days: int, pattern: str = "*") -> int:
    if days <= 0 or not parent.is_dir():
        return 0
    cutoff = time.time() - days * 86400
    removed = 0
    for path in parent.glob(pattern):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                removed += int(_remove(path))
        except OSError as exc:
            log.warning("retention: impossibile leggere %s (%s)", path, exc)
    return removed


def _read_object(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _pointer_versions(root: Path) -> set[str]:
    protected: set[str] = set()
    pointer_path = root / "active" / "current_version.json"
    if pointer_path.is_file():
        pointer = _read_object(pointer_path)
        if pointer is None or pointer.get("schema_version") != "seed.active-version.v1":
            return {path.name for path in _entries(root / "versions")}
        for key in ("version_id", "rollback_version"):
            if isinstance(pointer.get(key), str) and pointer[key]:
                protected.add(pointer[key])
    known_path = root / "recovery" / "known_good.json"
    if known_path.is_file():
        known = _read_object(known_path)
        if known is None or known.get("schema_version") != "seed.known-good.v1":
            return {path.name for path in _entries(root / "versions")}
        if isinstance(known.get("version_id"), str) and known["version_id"]:
            protected.add(known["version_id"])
    return protected


def _lineage_reachability(root: Path) -> _LineageReachability | None:
    events_dir = root / "lineage" / "events"
    if not events_dir.is_dir():
        return None
    statuses: dict[str, str] = {}
    parents: dict[str, str] = {}
    try:
        lineage = LineageStore(root / "lineage")
        lineage.verify_integrity()
        for event in lineage.events():
            mutation_id = str(event.get("mutation_id") or "")
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "candidate_created":
                candidate = payload.get("candidate") or {}
                if not mutation_id or not isinstance(candidate, dict):
                    return None
                status = candidate.get("status")
                parent = candidate.get("parent_version")
                if not isinstance(status, str) or not isinstance(parent, str):
                    return None
                statuses[mutation_id] = status
                parents[mutation_id] = parent
            elif event_type == "status_transition" and mutation_id:
                status = payload.get("to")
                if not isinstance(status, str) or mutation_id not in statuses:
                    return None
                statuses[mutation_id] = status
    except (OSError, json.JSONDecodeError, AttributeError, TypeError, LineageError):
        return None
    protected_mutations = {
        mutation_id for mutation_id, status in statuses.items()
        if status not in _TERMINAL_CANDIDATE_STATES
    }
    terminal = set(statuses) - protected_mutations
    protected_versions = set(protected_mutations)
    protected_versions.update(
        parents[mutation_id] for mutation_id in protected_mutations if mutation_id in parents
    )
    return _LineageReachability(
        frozenset(protected_versions),
        frozenset(protected_mutations),
        frozenset(terminal),
    )


def _prune_update_cache(root: Path, keep_history: int) -> dict[str, int]:
    updates = root / "operations" / "updates"
    if not updates.is_dir():
        return {"update_packages": 0, "update_history": 0}
    pending = updates / "pending_update.json"
    protected_package = ""
    if pending.is_file():
        value = _read_object(pending)
        if value is None or not isinstance(value.get("package"), str):
            return {"update_packages": 0, "update_history": 0}
        protected_package = value["package"]
    package_removed = 0
    for path in updates.iterdir():
        if (path.is_file() and path.name != protected_package
                and path.suffix.lower() in {".zip", ".exe"}):
            package_removed += int(_remove(path))
    history_removed = 0
    for name in ("applied", "failed"):
        history_removed += _prune_keep_recent(
            updates / name,
            keep_history,
            eligible=lambda path: bool(_UPDATE_HISTORY.match(path.name)),
            newest_key=_timestamp_prefix,
        )
    return {"update_packages": package_removed, "update_history": history_removed}


def prune_runtime_data(cfg: MaintenanceConfig) -> dict[str, int]:
    """Apply conservative retention; ambiguity always preserves artifacts."""
    if not cfg.enabled:
        return {}
    root = forbidden.seed_data_dir()
    reachability = _lineage_reachability(root)
    protected_versions = _pointer_versions(root)
    if reachability is not None:
        protected_versions.update(reachability.protected_versions)
    result = {
        "versions": _prune_keep_recent(
            root / "versions", cfg.keep_versions, protected=protected_versions),
        "backups": _prune_keep_recent(
            root / "operations" / "backups", cfg.keep_backups,
            eligible=lambda path: bool(_AUTO_BACKUP.match(path.name))),
        "runtime_backups": _prune_keep_recent(
            root / "recovery" / "runtime_backups",
            cfg.keep_runtime_backups,
            eligible=lambda path: bool(_TIMESTAMPED_ENTRY.match(path.name)),
            newest_key=_timestamp_prefix,
        ),
        "descendants": 0,
        "evaluator_runs": 0,
        "traces": _prune_old_files(
            root / "data" / "traces", cfg.trace_days, "*.jsonl"),
    }
    if reachability is not None:
        terminal = reachability.terminal_mutations
        result["descendants"] = _prune_keep_recent(
            root / "lab" / "descendants", cfg.keep_lab_runs,
            protected=reachability.protected_mutations,
            eligible=lambda path: path.name in terminal,
        )
        result["evaluator_runs"] = _prune_keep_recent(
            root / "lab" / "evaluator_runs", cfg.keep_lab_runs,
            protected={f"{item}.json" for item in reachability.protected_mutations},
            eligible=lambda path: path.stem in terminal,
        )
    result.update(_prune_update_cache(root, cfg.keep_update_history))
    total = sum(result.values())
    if total:
        log.info("retention: rimosse %d voci recuperabili %s", total, result)
    return result
