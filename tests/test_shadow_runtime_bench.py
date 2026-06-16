"""Executable synthetic benchmark remains privacy-safe and exposes weak layers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.shadow_runtime_bench import build_shadow_report  # noqa: E402


def test_shadow_runtime_benchmark_is_synthetic_and_executable():
    report = build_shadow_report()
    assert report["mode"] == "executable_synthetic_shadow"
    assert report["external_harnesses_executed"] is False
    assert report["privacy"] == {
        "synthetic_only": True,
        "real_user_data": False,
        "real_credentials": False,
        "network_calls_requested": False,
    }


def test_shadow_runtime_benchmark_closes_known_process_layer_gaps():
    report = build_shadow_report()
    by_id = {item["fixture_id"]: item for item in report["fixtures"]}
    assert by_id["outside_read_blocked"]["passed"]
    assert by_id["secret_env_stripped"]["passed"]
    assert by_id["timeout_kills_task"]["passed"]
    assert by_id["audit_blocks_subprocess"]["passed"]
    assert by_id["audit_blocks_network_without_declaration"]["passed"]
    assert by_id["runtime_subprocess_escape"]["passed"]
    assert by_id["runtime_network_socket_blocked"]["passed"]
    assert by_id["runtime_low_level_socket_blocked"]["passed"]
    assert report["summary"]["failed"] == 0
