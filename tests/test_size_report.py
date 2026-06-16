"""P2 size-regression budget: growth above 5 percent blocks the release unless a
documented reason is given (ProductionPlan: "crescita superiore al 5% richiede
motivazione"). Covers the previously-untested budget decision."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "size_report", ROOT / "scripts" / "size_report.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sr = _load()


# --- pure verdict ---------------------------------------------------------
def test_within_budget_is_allowed():
    v = sr.size_regression_verdict(102, 100)        # +2%
    assert v["delta_percent"] == 2.0
    assert v["exceeds_budget"] is False and v["allowed"] is True


def test_exact_threshold_is_not_a_regression():
    v = sr.size_regression_verdict(105, 100)        # +5% esatto, soglia stretta
    assert v["delta_percent"] == 5.0
    assert v["exceeds_budget"] is False and v["allowed"] is True


def test_over_budget_without_reason_is_blocked():
    v = sr.size_regression_verdict(106, 100)        # +6%
    assert v["exceeds_budget"] is True
    assert v["allowed"] is False and v["reason"] is None


def test_over_budget_with_documented_reason_is_allowed():
    v = sr.size_regression_verdict(200, 100, reason="aggiunto checkpoint emotion2vec")
    assert v["exceeds_budget"] is True
    assert v["allowed"] is True
    assert v["reason"] == "aggiunto checkpoint emotion2vec"


def test_blank_reason_does_not_unlock_budget():
    v = sr.size_regression_verdict(200, 100, reason="   ")
    assert v["allowed"] is False and v["reason"] is None


def test_non_positive_baseline_raises():
    with pytest.raises(ValueError):
        sr.size_regression_verdict(100, 0)


# --- main() I/O wiring ----------------------------------------------------
def _release_tree(root: Path, version: str, comp_bytes: int) -> None:
    app = root / "release" / version / "app" / "runtime"
    app.mkdir(parents=True)
    (app / "blob.bin").write_bytes(b"x" * comp_bytes)


def test_main_writes_report_when_within_budget(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sr, "ROOT", tmp_path)
    _release_tree(tmp_path, "0.0.0-test", 1000)
    rc = sr.main(["--version", "0.0.0-test", "--baseline-installed-bytes", "1000000"])
    assert rc == 0
    report = json.loads((tmp_path / "release" / "0.0.0-test" / "SIZE_REPORT.json")
                        .read_text(encoding="utf-8"))
    assert report["budget"]["allowed"] is True
    assert (tmp_path / "release" / "0.0.0-test" / "SIZE_REPORT.md").is_file()


def test_main_blocks_regression_without_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "ROOT", tmp_path)
    _release_tree(tmp_path, "0.0.0-big", 1000)
    with pytest.raises(RuntimeError, match="size regression"):
        sr.main(["--version", "0.0.0-big", "--baseline-installed-bytes", "100"])


def test_main_allows_regression_with_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "ROOT", tmp_path)
    _release_tree(tmp_path, "0.0.0-ok", 1000)
    rc = sr.main(["--version", "0.0.0-ok", "--baseline-installed-bytes", "100",
                  "--reason", "bundle ML completo richiesto"])
    assert rc == 0
    report = json.loads((tmp_path / "release" / "0.0.0-ok" / "SIZE_REPORT.json")
                        .read_text(encoding="utf-8"))
    assert report["budget"]["exceeds_budget"] is True
    assert report["budget"]["allowed"] is True
