"""Tests for the isolated S1-S5 practical acceptance runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.acceptance import CoreAcceptanceError, run_core_acceptance  # noqa: E402
from seed.core import forbidden  # noqa: E402


def test_core_acceptance_runs_full_synthetic_pipeline(tmp_path, monkeypatch):
    root = tmp_path / "acceptance"
    monkeypatch.setattr(
        forbidden,
        "seed_data_dir",
        lambda: (_ for _ in ()).throw(AssertionError("real SEED root accessed")),
    )

    report = run_core_acceptance(root)

    assert report["status"] == "passed"
    assert all(check["status"] == "pass" for check in report["checks"])
    assert report["synthetic_data"]["contains_real_user_data"] is False
    assert report["failure"] == ""
    persisted = json.loads(
        (root / "core_acceptance_report.json").read_text(encoding="utf-8")
    )
    assert persisted == report
    assert (root / "data" / "seed.db").is_file()
    assert (root / "lineage" / "events").is_dir()
    assert (root / "active" / "current_version.json").is_file()


def test_core_acceptance_refuses_nonempty_root(tmp_path):
    root = tmp_path / "acceptance"
    root.mkdir()
    (root / "existing.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(CoreAcceptanceError, match="must be empty"):
        run_core_acceptance(root)

    assert (root / "existing.txt").read_text(encoding="utf-8") == "keep"
