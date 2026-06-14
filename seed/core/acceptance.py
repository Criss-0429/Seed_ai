"""Isolated practical acceptance runner for the S1-S5 SEED core."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .descendant import DescendantBuilder, DescendantIntegrityError
from .evaluator import EvaluatorHarness
from .lineage import LineageStore, MutationCandidate
from .memory import Memory
from .promotion import PromotionAuthority, PromotionPolicy


_PRIVATE_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\bC:\\Users\\"),
)


class CoreAcceptanceError(RuntimeError):
    """Raised when the isolated acceptance run cannot prove a required check."""


@dataclass(frozen=True)
class AcceptanceCheck:
    check_id: str
    status: str
    details: str

    def to_dict(self) -> dict[str, str]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "details": self.details,
        }


class _CheckRecorder:
    def __init__(self) -> None:
        self.checks: list[AcceptanceCheck] = []

    def require(self, check_id: str, condition: bool, details: str) -> None:
        status = "pass" if condition else "fail"
        self.checks.append(AcceptanceCheck(check_id, status, details))
        if not condition:
            raise CoreAcceptanceError(f"{check_id}: {details}")


def run_core_acceptance(root: Path) -> dict[str, Any]:
    """Run S1-S5 with synthetic data under an empty, explicitly supplied root."""

    root = Path(root)
    _prepare_empty_root(root)
    recorder = _CheckRecorder()
    report_path = root / "core_acceptance_report.json"
    mutation_id = "acceptance-policy-001"
    memory: Memory | None = None
    status = "failed"
    failure = ""

    try:
        paths = _build_layout(root)
        _create_parent(paths["versions"])
        shutil.copytree(paths["versions"] / "parent-1" / "state", paths["state"])
        shutil.copytree(
            paths["versions"] / "parent-1" / "capabilities", paths["capabilities"]
        )
        _write_json(
            paths["active"] / "current_version.json",
            {
                "schema_version": "seed.active-version.v1",
                "version_id": "parent-1",
                "rollback_version": "parent-1",
            },
        )
        recorder.require(
            "isolated-root",
            all(_under(path, root) for path in paths.values()),
            "all acceptance paths stay under the supplied isolated root",
        )

        memory = Memory(paths["data"] / "seed.db")
        _seed_fake_memory(memory)
        memory.close()
        memory = Memory(paths["data"] / "seed.db")
        recorder.require(
            "synthetic-memory-reopen",
            len(memory.episodes_since(0)) == 3
            and len(memory.events_since(0)) == 2
            and memory.preferences().get("response_style") == "concise_with_context",
            "synthetic episodes, events, and preferences survive database reopen",
        )

        lineage, descendants, evaluator, authority = _components(paths)
        candidate = _candidate(mutation_id)
        proposal = _proposal()
        parent_policy = _read_json(paths["state"] / "policy.json")

        lineage.record_candidate(candidate, proposal=proposal)
        descendant_path, manifest = descendants.build(candidate, proposal)
        lineage.record_descendant(
            mutation_id,
            f"lab/descendants/{mutation_id}",
            manifest.content_hash,
            manifest.files,
        )
        candidate = lineage.transition(candidate, "built", reason="S5.5 synthetic build")
        evaluation = evaluator.evaluate(candidate, proposal)
        candidate = lineage.candidate(mutation_id)
        recorder.require(
            "build-evaluation-pass",
            evaluation.outcome == "pass"
            and candidate is not None
            and candidate.status == "validating",
            "state-based descendant builds and independent evaluator returns pass",
        )
        recorder.require(
            "evaluation-keeps-active-parent",
            _read_json(paths["state"] / "policy.json") == parent_policy,
            "build and evaluation do not change active state",
        )

        candidate = authority.start_shadow(candidate)
        recorder.require(
            "shadow-no-activation",
            candidate.status == "shadow"
            and _read_json(paths["state"] / "policy.json") == parent_policy,
            "shadow opens without changing active state",
        )
        authority.observe(mutation_id, "shadow", "pass", "synthetic-shadow-a")
        authority.observe(mutation_id, "shadow", "pass", "synthetic-shadow-b")
        lease = authority.start_canary(candidate, ["acceptance-context"])
        canary_policy = _read_json(
            authority.state_dir_for_context("acceptance-context") / "policy.json"
        )
        recorder.require(
            "canary-context-isolation",
            lease.active_for("acceptance-context")
            and canary_policy["rules"][0]["action"] == "silence"
            and authority.state_dir_for_context("ordinary-context") == paths["state"]
            and _read_json(paths["state"] / "policy.json") == parent_policy,
            "canary descendant is visible only to the leased context",
        )
        authority.observe(
            mutation_id,
            "canary",
            "pass",
            "synthetic-canary-a",
            context_id="acceptance-context",
        )
        authority.observe(
            mutation_id,
            "canary",
            "pass",
            "synthetic-canary-b",
            context_id="acceptance-context",
        )
        candidate = lineage.candidate(mutation_id)
        recorder.require(
            "promotion-gates-clear",
            candidate is not None and authority.promotion_blockers(candidate) == [],
            "evaluation, exposure, rollback, parent, and integrity gates are satisfied",
        )
        promoted = authority.promote(candidate)
        pointer = _read_json(paths["active"] / "current_version.json")
        recorder.require(
            "promotion-persists-active-version",
            promoted.status == "promoted"
            and _read_json(paths["state"] / "policy.json")["rules"][0]["action"] == "silence"
            and pointer["version_id"] == mutation_id
            and (paths["versions"] / mutation_id / "state").is_dir()
            and authority.lease(mutation_id) is None,
            "promotion updates active state and pointer and keeps a recoverable version",
        )

        reopened_lineage, _, reopened_evaluator, reopened_authority = _components(paths)
        reopened_candidate = reopened_lineage.candidate(mutation_id)
        recorder.require(
            "component-reopen-persistence",
            reopened_lineage.verify_integrity()
            and reopened_candidate is not None
            and reopened_candidate.status == "promoted"
            and reopened_evaluator.verify_report(mutation_id).outcome == "pass"
            and len(memory.episodes_since(0)) == 3,
            "new component instances reconstruct lineage, evaluation, active state, and memory",
        )
        rolled_back = reopened_authority.rollback(
            reopened_candidate, "S5.5 synthetic manual rollback"
        )
        recorder.require(
            "rollback-restores-parent",
            rolled_back.status == "rolled_back"
            and _read_json(paths["state"] / "policy.json") == parent_policy
            and _read_json(paths["active"] / "current_version.json")["version_id"]
            == "parent-1",
            "rollback restores parent state and active pointer",
        )

        tamper_candidate = _candidate("acceptance-tamper-001")
        reopened_lineage.record_candidate(tamper_candidate, proposal=proposal)
        tampered_path, _ = descendants.build(tamper_candidate, proposal)
        (tampered_path / "runtime" / "state" / "policy.json").write_text(
            "{}", encoding="utf-8"
        )
        tampering_detected = False
        try:
            descendants.verify(tampered_path)
        except DescendantIntegrityError:
            tampering_detected = True
        recorder.require(
            "descendant-tampering-detected",
            tampering_detected and reopened_lineage.verify_integrity(),
            "modified descendant is rejected while append-only lineage remains valid",
        )
        status = "passed"
    except Exception as exc:
        failure = _safe_failure(exc, root)
    finally:
        if memory is not None:
            memory.close()

    report = {
        "schema_version": "seed.core-acceptance.v1",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_root": "isolated_acceptance_root",
        "mutation_id": mutation_id,
        "checks": [check.to_dict() for check in recorder.checks],
        "synthetic_data": {
            "episodes": 3,
            "events": 2,
            "preferences": 2,
            "shadow_observations": 2,
            "canary_observations": 2,
            "contains_real_user_data": False,
        },
        "artifacts": {
            "memory": "data/seed.db",
            "lineage": "lineage/events/",
            "descendant": f"lab/descendants/{mutation_id}/",
            "evaluation": f"lab/evaluator_runs/{mutation_id}.json",
            "active_pointer": "active/current_version.json",
        },
        "limitations": [
            "shadow and canary observations are synthetic contract evidence",
            "no provider, network, UI, OPF inference, or real user data is used",
            "component reopen is not process crash recovery; S6 owns boot recovery",
            "state-based promotion does not execute a complete descendant runtime",
        ],
        "manual_validation_remaining": [
            "real OPF inference on consented test text",
            "real provider conversation and reflection quality",
            "human review of usefulness, predictability, and mutation explanation",
            "process crash, boot fallback, and known-good recovery after S6",
        ],
        "failure": failure,
    }
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
    report["checks"].append(
        AcceptanceCheck(
            "report-no-obvious-secrets",
            "pass" if not _contains_private_pattern(serialized) else "fail",
            "acceptance report contains no obvious secret, email, or Windows user path",
        ).to_dict()
    )
    if report["checks"][-1]["status"] == "fail":
        report["status"] = "failed"
    _write_json(report_path, report)
    return report


def _build_layout(root: Path) -> dict[str, Path]:
    return {
        "active": root / "active",
        "capabilities": root / "capabilities",
        "data": root / "data",
        "descendants": root / "lab" / "descendants",
        "evaluator_runs": root / "lab" / "evaluator_runs",
        "fixtures": root / "lab" / "replay_fixtures",
        "leases": root / "lab" / "canary_leases",
        "lineage": root / "lineage",
        "state": root / "state",
        "versions": root / "versions",
    }


def _components(
    paths: dict[str, Path],
) -> tuple[LineageStore, DescendantBuilder, EvaluatorHarness, PromotionAuthority]:
    lineage = LineageStore(paths["lineage"])
    descendants = DescendantBuilder(paths["descendants"], paths["versions"])
    evaluator = EvaluatorHarness(
        lineage, descendants, paths["evaluator_runs"], paths["fixtures"]
    )
    authority = PromotionAuthority(
        lineage,
        descendants,
        evaluator,
        paths["state"],
        paths["capabilities"],
        paths["versions"],
        paths["active"],
        paths["leases"],
        policy=PromotionPolicy(min_shadow_passes=2, min_canary_passes=2),
    )
    return lineage, descendants, evaluator, authority


def _candidate(mutation_id: str) -> MutationCandidate:
    return MutationCandidate(
        mutation_id=mutation_id,
        parent_version="parent-1",
        reason="Synthetic evidence suggests fewer interruptions during focus",
        evidence_refs=["episode:synthetic-focus-1", "preference:synthetic-1"],
        hypothesis="A focus silence policy reduces synthetic interruptions",
        target_scope=["policy"],
        expected_signals=[
            {
                "metric": "synthetic_interruptions",
                "direction": "decrease",
                "window": "acceptance-run",
            }
        ],
        evaluation_plan=["deterministic-replay", "shadow", "canary", "rollback"],
        risks=["safe"],
        permissions_delta=[],
        rollback_plan="parent-1",
        confidence=0.75,
    )


def _proposal() -> dict[str, Any]:
    return {
        "type": "policy_change",
        "target": "focus",
        "diff": {"trigger": "focus", "action": "silence"},
        "reason": "Synthetic evidence suggests fewer interruptions during focus",
        "expected_signal": "synthetic interruptions decrease",
        "risk_class": "safe",
        "permissions_delta": [],
    }


def _create_parent(versions: Path) -> None:
    parent = versions / "parent-1"
    (parent / "state").mkdir(parents=True)
    (parent / "capabilities").mkdir()
    _write_json(parent / "state" / "policy.json", {"rules": [], "suppressions": []})
    _write_json(
        parent / "state" / "user_model.json",
        {
            "facts": [],
            "hypotheses": [{"id": "synthetic-h1", "confidence": 0.35}],
            "interaction": {"verbosity": 0.5},
        },
    )
    _write_json(
        parent / "state" / "ui_manifest.json",
        {
            "theme": {"accent": "#888888"},
            "persona": {"tone": "neutral"},
            "widgets": ["chat"],
        },
    )


def _seed_fake_memory(memory: Memory) -> None:
    memory.add_episode(
        "survey",
        {"speaker": "[USER]", "text": "Synthetic user prefers concise explanations."},
        category="synthetic_preference",
    )
    memory.add_episode(
        "chat",
        {"speaker": "[USER]", "text": "Synthetic focus session interrupted twice."},
        category="synthetic_friction",
    )
    memory.add_episode(
        "system",
        {"result": "Synthetic focus session completed without interruption."},
        category="synthetic_outcome",
    )
    memory.set_preference("response_style", "concise_with_context", explicit=True)
    memory.set_preference("focus_interruptions", "minimize", explicit=True)
    memory.add_event("synthetic_feedback", {"useful": True, "score": 4})
    memory.add_event("synthetic_correction", {"category": "timing", "count": 1})


def _prepare_empty_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise CoreAcceptanceError(f"acceptance root must be empty: {root}")


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CoreAcceptanceError(f"expected JSON object: {path.name}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )


def _contains_private_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in _PRIVATE_PATTERNS)


def _safe_failure(exc: Exception, root: Path) -> str:
    text = f"{type(exc).__name__}: {exc}".replace(str(root), "<acceptance-root>")
    return re.sub(r"(?i)C:\\Users\\[^\\\s]+\\", r"C:\\Users\\[USER]\\", text)
