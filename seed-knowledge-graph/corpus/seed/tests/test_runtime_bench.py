"""D0 runtime option benchmark: deterministic, synthetic, privacy-safe."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.runtime_bench import build_runtime_benchmark, write_runtime_benchmark  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402


def test_benchmark_is_deterministic_and_hash_is_stable():
    first = build_runtime_benchmark()
    assert first == build_runtime_benchmark()
    assert len(first["report_hash"]) == 64
    assert first["external_runtime_execution"] is False


def test_fixtures_are_synthetic_and_privacy_safe():
    report = build_runtime_benchmark()
    assert report["privacy"] == {
        "fixtures_synthetic": True, "fixtures_redacted": True,
        "real_repo_used": False, "real_user_data_used": False,
        "secrets_used": False,
    }
    blob = json.dumps(report).lower()
    assert "api_key" not in blob
    assert "c:\\users\\" not in blob


def test_broad_runtime_authority_is_blocked():
    by_id = {r["option_id"]: r for r in build_runtime_benchmark()["results"]}
    assert "full_runtime_adoption_would_replace_seed_core" in by_id["openclaw"]["blockers"]
    assert "generic_shell_must_be_disabled_or_wrapped" in by_id["hermes"]["blockers"]
    assert by_id["openharness"]["blockers"] == []


def test_each_option_is_evaluated_against_every_fixture():
    report = build_runtime_benchmark()
    fixture_ids = {fixture["fixture_id"] for fixture in report["fixtures"]}
    for result in report["results"]:
        evaluated = {fixture["fixture_id"] for fixture in result["fixture_results"]}
        assert evaluated == fixture_ids
        assert all(fixture["verdict"] in {"pass", "partial"}
                   for fixture in result["fixture_results"])

    by_id = {r["option_id"]: r for r in report["results"]}
    openharness = {f["fixture_id"]: f for f in by_id["openharness"]["fixture_results"]}
    assert openharness["isolated_delegate_task"]["verdict"] == "pass"
    openclaw = {f["fixture_id"]: f for f in by_id["openclaw"]["fixture_results"]}
    assert "always_on_os_service" in openclaw["reviewable_heartbeat"]["forbidden_matches"]


def test_recommendation_keeps_seed_core_and_requires_owner_gate():
    rec = build_runtime_benchmark()["recommendation"]
    assert rec["execution_isolation_backend"] == "openharness"
    assert rec["registry_skills_delegation_pattern"] == "hermes"
    assert rec["daemon_session_pattern"] == "openclaw"
    assert rec["runtime_replacement"] == "none"
    assert rec["first_future_activation"] == "read_only"
    assert rec["next_phase_authorized"] is False


def test_write_report_is_auditable_and_reproducible(tmp_path):
    target = write_runtime_benchmark(tmp_path)
    assert json.loads(target.read_text(encoding="utf-8")) == build_runtime_benchmark()
    assert target.name == "runtime_option_benchmark_v1.json"


def test_runtimebench_command_is_local_and_returns_recommendation():
    class LocalOnly:
        @staticmethod
        def run_runtime_benchmark():
            return {"recommendation": {"runtime_replacement": "none"}}

    result = json.loads(SeedApp.handle_message(LocalOnly(), ":runtimebench"))
    assert result["recommendation"]["runtime_replacement"] == "none"
