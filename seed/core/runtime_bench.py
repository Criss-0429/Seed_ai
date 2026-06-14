"""D0 deterministic benchmark for agentic runtime options.

Evaluates architecture fit on synthetic privacy-safe fixtures. It never
installs, imports, starts, or contacts the compared runtimes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Criterion:
    key: str
    weight: int
    description: str


@dataclass(frozen=True)
class RuntimeOption:
    option_id: str
    role: str
    ratings: dict[str, int]
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    supported_patterns: tuple[str, ...]
    unsafe_patterns: tuple[str, ...] = ()
    requires_core_replacement: bool = False
    generic_shell_default: bool = False
    worker_receives_secrets: bool = False


@dataclass(frozen=True)
class SyntheticFixture:
    fixture_id: str
    required_patterns: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]
    redacted: bool = True
    synthetic: bool = True


@dataclass
class OptionResult:
    option_id: str
    role: str
    weighted_score: float
    criterion_scores: dict[str, int]
    strengths: list[str]
    risks: list[str]
    fixture_results: list[dict]
    blockers: list[str] = field(default_factory=list)


CRITERIA: tuple[Criterion, ...] = (
    Criterion("governance_fit", 20, "SEED Core retains authority and gates."),
    Criterion("isolation", 18, "Execution supports a restricted boundary."),
    Criterion("capability_delegation", 14, "Delegation is capability-specific."),
    Criterion("approval_dry_run", 13, "Approvals, hooks, and dry-run are explicit."),
    Criterion("skills_memory", 10, "Procedural skills are reviewable artifacts."),
    Criterion("session_daemon", 10, "Session isolation and heartbeat patterns."),
    Criterion("secrets_privacy", 10, "Workers operate without user secrets/content."),
    Criterion("operational_simplicity", 5, "Limited duplicated runtime complexity."),
)


OPTIONS: tuple[RuntimeOption, ...] = (
    RuntimeOption(
        "openharness", "execution_isolation_backend",
        {"governance_fit": 5, "isolation": 5, "capability_delegation": 4,
         "approval_dry_run": 5, "skills_memory": 3, "session_daemon": 2,
         "secrets_privacy": 5, "operational_simplicity": 4},
        ("dry_run", "permission_hooks", "workspace_isolation"),
        ("limited_daemon_patterns",),
        ("capability_specific", "audit", "no_secrets", "workspace_isolation",
         "typed_contract", "approval_hook"),
    ),
    RuntimeOption(
        "hermes", "registry_skills_delegation_pattern",
        {"governance_fit": 3, "isolation": 4, "capability_delegation": 5,
         "approval_dry_run": 3, "skills_memory": 5, "session_daemon": 3,
         "secrets_privacy": 3, "operational_simplicity": 2},
        ("typed_tool_registry", "reviewable_skills", "isolated_delegation"),
        ("runtime_overlap", "broad_tool_surface"),
        ("capability_specific", "audit", "no_secrets", "workspace_isolation",
         "typed_contract", "approval_hook"),
        ("generic_shell",),
        generic_shell_default=True,
    ),
    RuntimeOption(
        "openclaw", "daemon_session_pattern",
        {"governance_fit": 2, "isolation": 3, "capability_delegation": 3,
         "approval_dry_run": 2, "skills_memory": 4, "session_daemon": 5,
         "secrets_privacy": 3, "operational_simplicity": 2},
        ("heartbeat", "session_isolation", "sovereign_local_data"),
        ("runtime_overlap", "self_install_risk", "always_on_bias"),
        ("capability_specific", "audit", "session_isolation", "cooldown",
         "suppression"),
        ("generic_shell", "core_replacement", "always_on_os_service"),
        requires_core_replacement=True,
        generic_shell_default=True,
    ),
)


FIXTURES: tuple[SyntheticFixture, ...] = (
    SyntheticFixture("read_only_runtime_status",
                     ("capability_specific", "audit", "no_secrets"),
                     ("generic_shell", "real_user_data", "write_effect")),
    SyntheticFixture("reviewable_heartbeat",
                     ("session_isolation", "cooldown", "suppression"),
                     ("always_on_os_service", "silent_sensitive_action")),
    SyntheticFixture("isolated_delegate_task",
                     ("workspace_isolation", "typed_contract", "approval_hook"),
                     ("core_replacement", "unbounded_worker")),
)


def _blockers(option: RuntimeOption) -> list[str]:
    blockers = []
    if option.requires_core_replacement:
        blockers.append("full_runtime_adoption_would_replace_seed_core")
    if option.generic_shell_default:
        blockers.append("generic_shell_must_be_disabled_or_wrapped")
    if option.worker_receives_secrets:
        blockers.append("worker_secrets_forbidden")
    return blockers


def _weighted_score(option: RuntimeOption) -> float:
    total = sum(c.weight for c in CRITERIA)
    earned = sum(c.weight * option.ratings[c.key] / 5 for c in CRITERIA)
    return round(earned / total * 100, 2)


def _fixture_results(option: RuntimeOption) -> list[dict]:
    supported = set(option.supported_patterns)
    unsafe = set(option.unsafe_patterns)
    results = []
    for fixture in FIXTURES:
        missing = sorted(set(fixture.required_patterns) - supported)
        violations = sorted(set(fixture.forbidden_patterns) & unsafe)
        results.append({
            "fixture_id": fixture.fixture_id,
            "verdict": "pass" if not missing and not violations else "partial",
            "missing_requirements": missing,
            "forbidden_matches": violations,
        })
    return results


def _canonical_hash(report: dict) -> str:
    clean = dict(report)
    clean["report_hash"] = ""
    payload = json.dumps(clean, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_runtime_benchmark() -> dict:
    """Return deterministic D0 evidence without touching external runtimes."""
    results = [
        OptionResult(option.option_id, option.role, _weighted_score(option),
                     dict(option.ratings), list(option.strengths),
                     list(option.risks), _fixture_results(option),
                     _blockers(option))
        for option in OPTIONS
    ]
    results.sort(key=lambda result: (-result.weighted_score, result.option_id))
    report = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": "seed-d0-runtime-options-v1",
        "mode": "synthetic_architecture_fit",
        "external_runtime_execution": False,
        "privacy": {
            "fixtures_synthetic": all(f.synthetic for f in FIXTURES),
            "fixtures_redacted": all(f.redacted for f in FIXTURES),
            "real_repo_used": False,
            "real_user_data_used": False,
            "secrets_used": False,
        },
        "criteria": [asdict(criterion) for criterion in CRITERIA],
        "fixtures": [{
            "fixture_id": fixture.fixture_id,
            "required_patterns": list(fixture.required_patterns),
            "forbidden_patterns": list(fixture.forbidden_patterns),
            "redacted": fixture.redacted,
            "synthetic": fixture.synthetic,
        } for fixture in FIXTURES],
        "results": [asdict(result) for result in results],
        "recommendation": {
            "execution_isolation_backend": "openharness",
            "registry_skills_delegation_pattern": "hermes",
            "daemon_session_pattern": "openclaw",
            "integration_mode": "seed_governed_capability_specific_workers",
            "runtime_replacement": "none",
            "first_future_activation": "read_only",
            "next_phase_authorized": False,
        },
        "report_hash": "",
    }
    report["report_hash"] = _canonical_hash(report)
    return report


def write_runtime_benchmark(output_dir: Path) -> Path:
    """Atomically persist the privacy-safe D0 report."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "runtime_option_benchmark_v1.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(build_runtime_benchmark(), ensure_ascii=False, indent=2),
                    encoding="utf-8")
    temp.replace(target)
    return target
