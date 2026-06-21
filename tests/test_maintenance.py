"""Retention dati locali: tiene i piu' recenti, cancella il resto, rispetta i
limiti e l'opt-out. Usa SEED_DATA_ROOT su tmp_path: niente dati reali toccati."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden  # noqa: E402
from seed.core.config import MaintenanceConfig  # noqa: E402
from seed.core.maintenance import prune_runtime_data  # noqa: E402


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
    old = traces / "2020-01-01.jsonl"; old.write_text("{}", encoding="utf-8")
    new = traces / "today.jsonl"; new.write_text("{}", encoding="utf-8")
    os.utime(old, (time.time() - 60 * 86400,) * 2)
    res = prune_runtime_data(MaintenanceConfig(trace_days=30, keep_versions=0,
                                               keep_backups=0, keep_lab_runs=0))
    assert not old.exists() and new.exists()
    assert res["traces"] == 1
