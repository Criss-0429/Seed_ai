"""Retention dei dati locali rigenerabili.

Senza pulizia, %LOCALAPPDATA%\\SEED cresce a ogni sessione (snapshot di versione
a ogni reflection, backup a ogni migrazione/ripristino, run di lab, trace
giornaliere) e riempie l'SSD; un reinstall che conserva i dati se li porta
dietro. Questo modulo applica una retention semplice all'avvio: tiene i piu'
recenti N e cancella il resto. Tocca SOLO output rigenerabile, mai memoria,
config, credenziali o lineage.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from . import forbidden
from .config import MaintenanceConfig

log = logging.getLogger("seed.maintenance")


def _prune_keep_recent(parent: Path, keep: int) -> int:
    """Tiene le `keep` voci piu' recenti (per mtime) sotto `parent`, rimuove il
    resto. Ritorna quante ne ha rimosse. keep<=0 disattiva."""
    if keep <= 0 or not parent.is_dir():
        return 0
    entries = [p for p in parent.iterdir() if p.name not in (".", "..")]
    entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for old in entries[keep:]:
        try:
            shutil.rmtree(old) if old.is_dir() else old.unlink()
            removed += 1
        except Exception as exc:
            log.warning("retention: impossibile rimuovere %s (%s)", old, exc)
    return removed


def _prune_old_files(parent: Path, days: int, pattern: str = "*") -> int:
    """Rimuove i file piu' vecchi di `days` giorni. days<=0 disattiva."""
    if days <= 0 or not parent.is_dir():
        return 0
    cutoff = time.time() - days * 86400
    removed = 0
    for f in parent.glob(pattern):
        try:
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception as exc:
            log.warning("retention: impossibile rimuovere %s (%s)", f, exc)
    return removed


def prune_runtime_data(cfg: MaintenanceConfig) -> dict[str, int]:
    """Applica la retention. Ritorna il conteggio rimosso per categoria."""
    if not cfg.enabled:
        return {}
    root = forbidden.seed_data_dir()
    result = {
        "versions": _prune_keep_recent(root / "versions", cfg.keep_versions),
        "backups": _prune_keep_recent(
            root / "operations" / "backups", cfg.keep_backups),
        "descendants": _prune_keep_recent(
            root / "lab" / "descendants", cfg.keep_lab_runs),
        "evaluator_runs": _prune_keep_recent(
            root / "lab" / "evaluator_runs", cfg.keep_lab_runs),
        "traces": _prune_old_files(
            root / "data" / "traces", cfg.trace_days, "*.jsonl"),
    }
    total = sum(result.values())
    if total:
        log.info("retention: rimosse %d voci rigenerabili %s", total, result)
    return result
