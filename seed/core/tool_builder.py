"""Governed real-tool forge: stage, audit, isolated test, owner install."""

from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from . import sandbox

_SAFE_ID = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")


@dataclass(frozen=True)
class ToolCandidate:
    capability_id: str
    candidate_dir: Path
    audit_passed: bool
    test_passed: bool
    violations: tuple[str, ...]


class GovernedToolBuilder:
    def __init__(self, registry, staging_root: Path, *, enabled: bool = False, audit=None):
        self.registry = registry
        self.staging_root = Path(staging_root)
        self.enabled = bool(enabled)
        self.audit = audit or (lambda kind, payload: None)
        self.staging_root.mkdir(parents=True, exist_ok=True)

    def stage(self, manifest: dict, code: str, *, backend: str = "process") -> ToolCandidate:
        capability_id = str(manifest.get("capability_id") or "")
        violations = list(self.registry_validate(manifest))
        if not _SAFE_ID.fullmatch(capability_id):
            violations.append("capability_id non sicuro")
        static = sandbox.static_audit(code, needs_network=bool(manifest.get("needs_network")))
        violations.extend(static.violations)
        target = self.staging_root / capability_id if capability_id else self.staging_root / "_invalid"
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)
        (target / "tool.py").write_text(code, encoding="utf-8")
        (target / "manifest.json").write_text(
            json.dumps({**manifest, "origin": "generated", "state": "proposed"},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        test = sandbox.run_tool(
            target, {**{k: "test" for k in (manifest.get("input_schema") or {})},
                     "__dry_run__": True},
            timeout=30, backend=backend,
            network_allowed=bool(manifest.get("needs_network")))
        if not test.ok:
            violations.append(f"isolated test failed: {test.stderr}")
        record = {
            "schema_version": "seed.tool-candidate.v1",
            "capability_id": capability_id,
            "audit_passed": static.passed,
            "test_passed": test.ok,
            "violations": violations,
            "backend": backend,
            "created_at": time.time(),
        }
        (target / "REVIEW.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        self.audit("tool_candidate_staged", {
            "capability_id": capability_id, "passed": not violations, "backend": backend})
        return ToolCandidate(capability_id, target, static.passed, test.ok, tuple(violations))

    def install(self, candidate: ToolCandidate, *, owner_approved: bool,
                reviewer_passed: bool) -> tuple[bool, list[str]]:
        if not self.enabled:
            return False, ["tool_builder_disabled"]
        if not owner_approved:
            return False, ["owner_approval_required"]
        if not reviewer_passed:
            return False, ["reviewer_pass_required"]
        if candidate.violations or not candidate.audit_passed or not candidate.test_passed:
            return False, list(candidate.violations) or ["candidate_not_passed"]
        manifest = json.loads((candidate.candidate_dir / "manifest.json").read_text(encoding="utf-8"))
        code = (candidate.candidate_dir / "tool.py").read_text(encoding="utf-8")
        ok, errors = self.registry.register_generated(manifest, code)
        self.audit("tool_candidate_install", {
            "capability_id": candidate.capability_id, "installed": ok,
            "owner_approved": owner_approved, "reviewer_passed": reviewer_passed})
        return ok, errors

    def registry_validate(self, manifest: dict) -> list[str]:
        from .capabilities import validate_manifest
        return validate_manifest({**manifest, "origin": "generated"})


