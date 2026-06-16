"""Deterministic replay and independent descendant evaluation.

S4 evaluates isolated artifacts and state. It never calls a provider, executes
descendant code, starts shadow/canary, or changes the active runtime.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Any

from .descendant import DescendantBuilder, DescendantIntegrityError
from .lineage import LineageStore, MutationCandidate


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_OBVIOUS_PRIVATE_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b"),
    re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b", re.IGNORECASE),
    re.compile(r"(?i)\bC:\\Users\\(?!\[USER\])[^\\\s]+\\"),
)
_RUNTIME_ONLY_SCOPES = {
    "architecture", "core", "evaluator", "governance", "lineage",
    "recovery", "supervisor",
}


class EvaluationError(ValueError):
    """Raised when an evaluation run cannot be trusted or reproduced."""


class EvaluationIntegrityError(EvaluationError):
    """Raised when a persisted evaluation report has been altered."""


@dataclass(frozen=True)
class ReplayAssertion:
    assertion_id: str
    file: str
    operator: str
    path: str = ""
    expected: Any = None

    def validate(self) -> None:
        if not _nonempty(self.assertion_id):
            raise EvaluationError("replay assertion_id is required")
        _safe_relative(self.file, "replay assertion file")
        if self.operator not in {
            "equals", "contains", "exists", "file_exists", "file_absent", "unchanged",
        }:
            raise EvaluationError(f"unsupported replay operator: {self.operator}")
        if self.operator in {"equals", "contains", "exists", "unchanged"} and not _nonempty(
            self.path
        ):
            raise EvaluationError(f"replay path required for {self.operator}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReplayAssertion":
        if not isinstance(data, dict):
            raise EvaluationError("replay assertion must be an object")
        try:
            assertion = cls(**data)
        except TypeError as exc:
            raise EvaluationError(f"invalid replay assertion: {exc}") from exc
        assertion.validate()
        return assertion


@dataclass(frozen=True)
class ReplayFixture:
    fixture_id: str
    source: str
    redacted: bool
    assertions: list[ReplayAssertion]
    source_ref: str = ""

    def validate(self) -> None:
        if not _nonempty(self.fixture_id) or not _nonempty(self.source):
            raise EvaluationError("replay fixture_id and source are required")
        if self.redacted is not True:
            raise EvaluationError(f"replay fixture is not redacted: {self.fixture_id}")
        if not self.assertions:
            raise EvaluationError(f"replay fixture has no assertions: {self.fixture_id}")
        for assertion in self.assertions:
            assertion.validate()
        serialized = _canonical_json(self.to_dict(scan=False))
        if _contains_obvious_private_data(serialized):
            raise EvaluationError(
                f"replay fixture contains obvious private data or secret: {self.fixture_id}"
            )

    def to_dict(self, *, scan: bool = True) -> dict[str, Any]:
        data = {
            "fixture_id": self.fixture_id,
            "source": self.source,
            "redacted": self.redacted,
            "source_ref": self.source_ref,
            "assertions": [assertion.to_dict() for assertion in self.assertions],
        }
        if scan:
            self.validate()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReplayFixture":
        if not isinstance(data, dict):
            raise EvaluationError("replay fixture must be an object")
        try:
            fixture = cls(
                fixture_id=data["fixture_id"],
                source=data["source"],
                redacted=data["redacted"],
                source_ref=data.get("source_ref", ""),
                assertions=[
                    ReplayAssertion.from_dict(item)
                    for item in data.get("assertions", [])
                ],
            )
        except KeyError as exc:
            raise EvaluationError(f"replay fixture missing field: {exc.args[0]}") from exc
        fixture.validate()
        return fixture


@dataclass(frozen=True)
class EvaluationCheck:
    check_id: str
    outcome: str
    details: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not _nonempty(self.check_id) or not _nonempty(self.details):
            raise EvaluationError("evaluation check id and details are required")
        if self.outcome not in {"pass", "fail", "inconclusive"}:
            raise EvaluationError(f"invalid evaluation check outcome: {self.outcome}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class EvaluationReport:
    schema_version: str
    evaluator_id: str
    mutation_id: str
    parent_version: str
    descendant_content_hash: str
    corpus_hash: str
    outcome: str
    checks: list[EvaluationCheck]
    descendant_executed: bool = False
    provider_called: bool = False
    report_hash: str = ""

    def validate(self) -> None:
        if self.schema_version != "seed.evaluation.v1":
            raise EvaluationError(f"unsupported evaluation schema: {self.schema_version}")
        for value in (
            self.evaluator_id,
            self.mutation_id,
            self.parent_version,
            self.descendant_content_hash,
            self.corpus_hash,
        ):
            if not _nonempty(value):
                raise EvaluationError("evaluation report required field missing")
        if self.outcome not in {"pass", "fail", "inconclusive"}:
            raise EvaluationError(f"invalid evaluation report outcome: {self.outcome}")
        if not self.checks:
            raise EvaluationError("evaluation report has no checks")
        for check in self.checks:
            check.validate()
        if self.descendant_executed or self.provider_called:
            raise EvaluationError("S4 report cannot execute descendant or call provider")
        expected = _report_hash(self)
        if self.report_hash and self.report_hash != expected:
            raise EvaluationIntegrityError("evaluation report hash differs")

    def with_hash(self) -> "EvaluationReport":
        report = replace(self, report_hash="")
        return replace(report, report_hash=_report_hash(report))

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            **asdict(self),
            "checks": [check.to_dict() for check in self.checks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationReport":
        if not isinstance(data, dict):
            raise EvaluationIntegrityError("evaluation report must be an object")
        try:
            report = cls(
                **{
                    **data,
                    "checks": [
                        EvaluationCheck(**item) for item in data.get("checks", [])
                    ],
                }
            )
        except (TypeError, KeyError) as exc:
            raise EvaluationIntegrityError(f"invalid evaluation report: {exc}") from exc
        report.validate()
        return report


class EvaluatorHarness:
    EVALUATOR_ID = "independent-replay-harness-v1"

    def __init__(
        self,
        lineage: LineageStore,
        descendant_builder: DescendantBuilder,
        evaluator_runs_root: Path,
        replay_fixtures_root: Path,
    ):
        self.lineage = lineage
        self.descendant_builder = descendant_builder
        self.evaluator_runs_root = Path(evaluator_runs_root)
        self.replay_fixtures_root = Path(replay_fixtures_root)
        self.evaluator_runs_root.mkdir(parents=True, exist_ok=True)
        self.replay_fixtures_root.mkdir(parents=True, exist_ok=True)

    def evaluate(
        self,
        candidate: MutationCandidate,
        proposal: dict[str, Any],
    ) -> EvaluationReport:
        candidate.validate()
        self.lineage.verify_integrity()
        recorded = self.lineage.candidate(candidate.mutation_id)
        if recorded is None:
            raise EvaluationError(f"candidate missing from lineage: {candidate.mutation_id}")
        status = recorded.status
        if status == "built":
            recorded = self.lineage.transition(
                recorded, "validating", reason="S4 deterministic evaluator started"
            )
        elif status != "validating":
            raise EvaluationError(f"candidate cannot be evaluated from status: {status}")

        descendant_dir = self.descendant_builder.descendants_root / candidate.mutation_id
        try:
            manifest = self.descendant_builder.verify(descendant_dir)
        except DescendantIntegrityError as exc:
            raise EvaluationIntegrityError(str(exc)) from exc
        if manifest.parent_version != candidate.parent_version:
            raise EvaluationIntegrityError("candidate and descendant parent differ")
        if not isinstance(proposal, dict):
            raise EvaluationError("proposal must be an object")
        if self.lineage.proposal(candidate.mutation_id) != proposal:
            raise EvaluationIntegrityError("proposal differs from append-only lineage")

        fixtures = [_fixture_from_proposal(candidate, proposal)]
        fixtures.extend(self.load_fixtures())
        corpus_hash = _hash_data([fixture.to_dict() for fixture in fixtures])
        parent_dir = self.descendant_builder.versions_dir / candidate.parent_version
        runtime_dir = descendant_dir / "runtime"

        checks = [
            EvaluationCheck(
                "lineage-integrity",
                "pass",
                "append-only lineage hash chain verified",
            ),
            EvaluationCheck(
                "descendant-integrity",
                "pass",
                "descendant manifest and file hashes verified",
                {"content_hash": manifest.content_hash},
            ),
            _scope_check(parent_dir, runtime_dir, proposal),
            _permission_contract_check(candidate, proposal),
            _private_data_check(runtime_dir),
            _run_replay(parent_dir, runtime_dir, fixtures),
            _runtime_evidence_check(candidate, proposal),
        ]
        outcome = _aggregate_outcome(checks)
        report = EvaluationReport(
            schema_version="seed.evaluation.v1",
            evaluator_id=self.EVALUATOR_ID,
            mutation_id=candidate.mutation_id,
            parent_version=candidate.parent_version,
            descendant_content_hash=manifest.content_hash,
            corpus_hash=corpus_hash,
            outcome=outcome,
            checks=checks,
        ).with_hash()
        report_path = self._persist_report(report)
        report_ref = report_path.relative_to(self.evaluator_runs_root.parent.parent).as_posix()
        self.lineage.record_evaluation(
            candidate.mutation_id,
            self.EVALUATOR_ID,
            outcome,
            metrics={
                "report_ref": report_ref,
                "report_hash": report.report_hash,
                "checks": len(checks),
                "failed_checks": sum(check.outcome == "fail" for check in checks),
                "inconclusive_checks": sum(
                    check.outcome == "inconclusive" for check in checks
                ),
                "descendant_executed": False,
                "provider_called": False,
            },
            notes="S4 deterministic replay; no descendant execution or activation.",
        )
        if outcome == "fail":
            current = self.lineage.candidate(candidate.mutation_id)
            if current is not None and current.status == "validating":
                self.lineage.transition(
                    current, "rejected", reason="S4 evaluator found blocking regression"
                )
        return report

    def load_fixtures(self) -> list[ReplayFixture]:
        fixtures: list[ReplayFixture] = []
        for path in sorted(self.replay_fixtures_root.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise EvaluationError(f"invalid replay fixture file: {path.name}") from exc
            items = raw if isinstance(raw, list) else [raw]
            fixtures.extend(ReplayFixture.from_dict(item) for item in items)
        ids = [fixture.fixture_id for fixture in fixtures]
        if len(ids) != len(set(ids)):
            raise EvaluationError("duplicate replay fixture_id")
        return fixtures

    def verify_report(self, mutation_id: str) -> EvaluationReport:
        _safe_component(mutation_id, "mutation_id")
        path = self.evaluator_runs_root / f"{mutation_id}.json"
        if not path.is_file():
            raise EvaluationIntegrityError(f"evaluation report missing: {mutation_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvaluationIntegrityError("unreadable evaluation report") from exc
        return EvaluationReport.from_dict(raw)

    def _persist_report(self, report: EvaluationReport) -> Path:
        _safe_component(report.mutation_id, "mutation_id")
        path = self.evaluator_runs_root / f"{report.mutation_id}.json"
        if path.exists():
            existing = self.verify_report(report.mutation_id)
            if existing != report:
                raise EvaluationIntegrityError(
                    f"existing evaluation report differs: {report.mutation_id}"
                )
            return path
        _atomic_create_json(path, report.to_dict())
        return path


def _fixture_from_proposal(
    candidate: MutationCandidate,
    proposal: dict[str, Any],
) -> ReplayFixture:
    mtype = proposal.get("type")
    target = str(proposal.get("target") or "")
    diff = proposal.get("diff")
    if not isinstance(diff, dict):
        raise EvaluationError("proposal diff must be an object")
    assertions: list[ReplayAssertion] = []

    if mtype == "trait_change":
        assertions.append(
            ReplayAssertion(
                "proposal-trait-value",
                "state/user_model.json",
                "equals",
                target,
                diff.get("value", diff),
            )
        )
    elif mtype in {"ui_change", "persona_change"}:
        section = "persona" if mtype == "persona_change" else "theme"
        for key, value in sorted(diff.items()):
            path = key if mtype == "ui_change" and key == "widgets" else f"{section}.{key}"
            assertions.append(
                ReplayAssertion(f"proposal-{mtype}-{key}", "state/ui_manifest.json",
                                "equals", path, value)
            )
    elif mtype == "policy_change":
        assertions.append(
            ReplayAssertion(
                "proposal-policy-rule",
                "state/policy.json",
                "contains",
                "rules",
                diff,
            )
        )
    elif mtype == "new_capability":
        capability_id = str((diff.get("manifest") or {}).get("capability_id") or target)
        _safe_component(capability_id, "capability_id")
        assertions.extend([
            ReplayAssertion(
                "proposal-capability-manifest",
                f"capabilities/{capability_id}/manifest.json",
                "file_exists",
            ),
            ReplayAssertion(
                "proposal-capability-code",
                f"capabilities/{capability_id}/tool.py",
                "file_exists",
            ),
        ])
    elif mtype == "prune_capability":
        _safe_component(target, "capability target")
        assertions.extend([
            ReplayAssertion(
                "proposal-pruned-capability-absent",
                f"capabilities/{target}/manifest.json",
                "file_absent",
            ),
            ReplayAssertion(
                "proposal-pruned-capability-recorded",
                "overlays/pruned_capabilities.json",
                "contains",
                "capability_ids",
                target,
            ),
        ])
    else:
        raise EvaluationError(f"unsupported proposal type for replay: {mtype}")

    fixture = ReplayFixture(
        fixture_id=f"proposal-{candidate.mutation_id}",
        source="generated_contract",
        redacted=True,
        source_ref=f"candidate:{candidate.mutation_id}",
        assertions=assertions,
    )
    fixture.validate()
    return fixture


def _run_replay(
    parent_dir: Path,
    runtime_dir: Path,
    fixtures: list[ReplayFixture],
) -> EvaluationCheck:
    failures: list[str] = []
    assertions_run = 0
    for fixture in fixtures:
        fixture.validate()
        for assertion in fixture.assertions:
            assertions_run += 1
            ok, detail = _evaluate_assertion(parent_dir, runtime_dir, assertion)
            if not ok:
                failures.append(f"{fixture.fixture_id}/{assertion.assertion_id}: {detail}")
    if failures:
        return EvaluationCheck(
            "deterministic-replay",
            "fail",
            "one or more replay assertions failed",
            {"fixtures": len(fixtures), "assertions": assertions_run, "failures": failures},
        )
    return EvaluationCheck(
        "deterministic-replay",
        "pass",
        "all deterministic replay assertions passed",
        {"fixtures": len(fixtures), "assertions": assertions_run},
    )


def _evaluate_assertion(
    parent_dir: Path,
    runtime_dir: Path,
    assertion: ReplayAssertion,
) -> tuple[bool, str]:
    assertion.validate()
    relative = Path(PurePosixPath(assertion.file))
    descendant_file = runtime_dir / relative
    parent_file = parent_dir / relative
    if assertion.operator == "file_exists":
        return descendant_file.is_file(), f"file missing: {assertion.file}"
    if assertion.operator == "file_absent":
        return not descendant_file.exists(), f"file still exists: {assertion.file}"
    try:
        descendant_data = json.loads(descendant_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, f"unreadable JSON: {assertion.file}"
    found, value = _json_path(descendant_data, assertion.path)
    if assertion.operator == "exists":
        return found, f"path missing: {assertion.path}"
    if not found:
        return False, f"path missing: {assertion.path}"
    if assertion.operator == "equals":
        return value == assertion.expected, f"value differs at {assertion.path}"
    if assertion.operator == "contains":
        return _contains(value, assertion.expected), f"value not contained at {assertion.path}"
    if assertion.operator == "unchanged":
        try:
            parent_data = json.loads(parent_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False, f"unreadable parent JSON: {assertion.file}"
        parent_found, parent_value = _json_path(parent_data, assertion.path)
        return found == parent_found and value == parent_value, (
            f"value changed at {assertion.path}"
        )
    return False, f"unsupported operator: {assertion.operator}"


def _scope_check(parent_dir: Path, runtime_dir: Path, proposal: dict[str, Any]) -> EvaluationCheck:
    changed = _changed_files(parent_dir, runtime_dir)
    mtype = proposal.get("type")
    target = str(proposal.get("target") or "")
    diff = proposal.get("diff") if isinstance(proposal.get("diff"), dict) else {}
    allowed_exact: set[str] = set()
    allowed_prefixes: tuple[str, ...] = ()
    if mtype == "trait_change":
        allowed_exact = {"state/user_model.json"}
    elif mtype in {"ui_change", "persona_change"}:
        allowed_exact = {"state/ui_manifest.json"}
    elif mtype == "policy_change":
        allowed_exact = {"state/policy.json"}
    elif mtype == "new_capability":
        capability_id = str((diff.get("manifest") or {}).get("capability_id") or target)
        _safe_component(capability_id, "capability_id")
        allowed_prefixes = (f"capabilities/{capability_id}/",)
    elif mtype == "prune_capability":
        _safe_component(target, "capability target")
        allowed_exact = {"overlays/pruned_capabilities.json"}
        allowed_prefixes = (f"capabilities/{target}/",)
    unexpected = sorted(
        path for path in changed
        if path not in allowed_exact and not path.startswith(allowed_prefixes)
    )
    if not changed:
        return EvaluationCheck(
            "declared-scope",
            "fail",
            "proposal produced no observable descendant change",
            {"changed_files": []},
        )
    if unexpected:
        return EvaluationCheck(
            "declared-scope",
            "fail",
            "descendant changed files outside declared proposal scope",
            {"changed_files": changed, "unexpected_files": unexpected},
        )
    return EvaluationCheck(
        "declared-scope",
        "pass",
        "all descendant changes stay inside declared proposal scope",
        {"changed_files": changed},
    )


def _permission_contract_check(
    candidate: MutationCandidate,
    proposal: dict[str, Any],
) -> EvaluationCheck:
    proposal_delta = proposal.get("permissions_delta", [])
    if not isinstance(proposal_delta, list):
        return EvaluationCheck(
            "permission-contract",
            "fail",
            "proposal permissions_delta is not a list",
        )
    risk_class = str(proposal.get("risk_class") or "unknown")
    problems: list[str] = []
    if proposal_delta != candidate.permissions_delta:
        problems.append("permissions_delta differs between candidate and proposal")
    if risk_class not in candidate.risks:
        problems.append("risk_class differs between candidate and proposal")
    if problems:
        return EvaluationCheck(
            "permission-contract",
            "fail",
            "permission or risk declaration mismatch",
            {"problems": problems},
        )
    return EvaluationCheck(
        "permission-contract",
        "pass",
        "permission delta and risk declaration match append-only candidate",
        {"permissions_delta_count": len(candidate.permissions_delta), "risk_class": risk_class},
    )


def _private_data_check(runtime_dir: Path) -> EvaluationCheck:
    flagged: list[str] = []
    for path in sorted(p for p in runtime_dir.rglob("*") if p.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _contains_obvious_private_data(text):
            flagged.append(path.relative_to(runtime_dir).as_posix())
    if flagged:
        return EvaluationCheck(
            "obvious-secret-scan",
            "fail",
            "obvious private data or secret pattern found in descendant",
            {"flagged_files": flagged},
        )
    return EvaluationCheck(
        "obvious-secret-scan",
        "pass",
        "no obvious private data or secret pattern found in descendant",
    )


def _runtime_evidence_check(
    candidate: MutationCandidate,
    proposal: dict[str, Any],
) -> EvaluationCheck:
    scopes = {scope.lower() for scope in candidate.target_scope}
    if proposal.get("type") == "new_capability" or scopes & _RUNTIME_ONLY_SCOPES:
        return EvaluationCheck(
            "runtime-evidence",
            "inconclusive",
            "candidate requires isolated runtime execution beyond S4 state replay",
            {"descendant_executed": False},
        )
    return EvaluationCheck(
        "runtime-evidence",
        "pass",
        "candidate scope is fully assessable by S4 deterministic state replay",
        {"descendant_executed": False},
    )


def _aggregate_outcome(checks: list[EvaluationCheck]) -> str:
    if any(check.outcome == "fail" for check in checks):
        return "fail"
    if any(check.outcome == "inconclusive" for check in checks):
        return "inconclusive"
    return "pass"


def _changed_files(parent_dir: Path, runtime_dir: Path) -> list[str]:
    parent_hashes = _file_hashes(parent_dir)
    runtime_hashes = _file_hashes(runtime_dir)
    return sorted(
        path for path in set(parent_hashes) | set(runtime_hashes)
        if parent_hashes.get(path) != runtime_hashes.get(path)
    )


def _file_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise EvaluationError(f"evaluation root missing: {root.name}")
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(p for p in root.rglob("*") if p.is_file())
    }


def _json_path(data: Any, path: str) -> tuple[bool, Any]:
    value = data
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return False, None
    return True, value


def _contains(container: Any, expected: Any) -> bool:
    if isinstance(container, list):
        if isinstance(expected, dict):
            return any(
                isinstance(item, dict)
                and all(item.get(key) == value for key, value in expected.items())
                for item in container
            )
        return expected in container
    if isinstance(container, dict) and isinstance(expected, dict):
        return all(container.get(key) == value for key, value in expected.items())
    if isinstance(container, str) and isinstance(expected, str):
        return expected in container
    return False


def _contains_obvious_private_data(text: str) -> bool:
    return any(pattern.search(text) for pattern in _OBVIOUS_PRIVATE_PATTERNS)


def _safe_component(value: str, field_name: str) -> None:
    if not _SAFE_COMPONENT.fullmatch(value):
        raise EvaluationError(f"unsafe {field_name}: {value!r}")


def _safe_relative(value: str, field_name: str) -> None:
    if not _nonempty(value):
        raise EvaluationError(f"{field_name} is required")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise EvaluationError(f"unsafe {field_name}: {value!r}")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_data(data: Any) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()


def _report_hash(report: EvaluationReport) -> str:
    data = asdict(report)
    data["report_hash"] = ""
    return _hash_data(data)


def _atomic_create_json(path: Path, data: dict[str, Any]) -> None:
    if path.exists():
        raise EvaluationIntegrityError(f"append-only report already exists: {path.name}")
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".evaluation-",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.flush()
        temp_path = Path(handle.name)
    try:
        if path.exists():
            raise EvaluationIntegrityError(f"append-only report already exists: {path.name}")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
