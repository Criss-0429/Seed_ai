"""D5: skills procedurali + delega (doc 16).

- **Skills** = ricette procedurali (sequenza di capability gia' allowlistate),
  riviste come evidenza (audit + reviewer) e installate SOLO con owner gate:
  niente self-install autonomo, niente codice arbitrario eseguito qui;
- **Task Graph IR** = DAG tipato di step, ognuno riferito a una capability
  allowlistata; validazione deterministica (no cicli, dipendenze esistenti);
- **delega** a sub-agenti isolati (processo ristretto/container/worktree):
  esecuzione reale gated di task graph allowlistati.

Confini D5: default OFF; nessuna skill attiva senza review + owner gate; nessun
self-install; `destructive` vietata; ogni step passa comunque dai gate worker
(D2 read / D4 write-safe). Nessuna shell o capability non allowlistata.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .isolation import IsolationPolicy, IsolationResult, backend_available, run_python
from . import sandbox

log = logging.getLogger("seed.skills")

SCHEMA_VERSION = "seed.skills.v1"

_FORBIDDEN_RISK = frozenset({"destructive", "critical"})
_DELEGATION_ISOLATION = ("worktree", "container")


class SkillError(ValueError):
    pass


@dataclass(frozen=True)
class SkillStep:
    capability_id: str            # deve essere una capability/azione allowlistata
    description: str = ""


@dataclass(frozen=True)
class Skill:
    skill_id: str
    description: str
    steps: tuple[SkillStep, ...]
    risk_class: str = "read_safe"

    def validate(self) -> None:
        if not self.skill_id.strip():
            raise SkillError("skill_id mancante")
        if not self.steps:
            raise SkillError("skill senza step")
        if self.risk_class in _FORBIDDEN_RISK:
            raise SkillError(f"risk_class vietata: {self.risk_class}")


@dataclass(frozen=True)
class SkillAudit:
    skill_id: str
    passed: bool
    violations: tuple[str, ...]


def audit_skill(skill: Skill, *, allowed_capabilities: frozenset[str]) -> SkillAudit:
    """Audit deterministico: ogni step deve riferire una capability allowlistata;
    niente rischio vietato. NON esegue nulla."""
    violations: list[str] = []
    try:
        skill.validate()
    except SkillError as exc:
        violations.append(str(exc))
    for step in skill.steps:
        if step.capability_id not in allowed_capabilities:
            violations.append(f"capability non allowlistata: {step.capability_id}")
    return SkillAudit(skill.skill_id, not violations, tuple(violations))


class SkillRegistry:
    """Registry skill review-gated. Default vuoto; nessun self-install."""

    def __init__(self, *, enabled: bool = False,
                 allowed_capabilities: tuple[str, ...] = (), audit=None):
        self._enabled = bool(enabled)
        self._allowed = frozenset(allowed_capabilities)
        self._audit = audit or (lambda kind, payload: None)
        self._skills: dict[str, Skill] = {}

    def install(self, skill: Skill, *, owner_approved: bool,
                reviewer_passed: bool) -> SkillAudit:
        """Installa una skill SOLO con audit pass + reviewer + owner gate.

        L'owner gate e' obbligatorio: nessun self-install autonomo."""
        result = audit_skill(skill, allowed_capabilities=self._allowed)
        gated = (self._enabled and result.passed and reviewer_passed
                 and owner_approved)
        if gated:
            self._skills[skill.skill_id] = skill
        self._audit("skill_install", {
            "schema_version": SCHEMA_VERSION,
            "skill_id": skill.skill_id,
            "installed": gated,
            "audit_passed": result.passed,
            "reviewer_passed": bool(reviewer_passed),
            "owner_approved": bool(owner_approved),
        })
        if not gated and not result.passed:
            return result
        if not gated:
            return SkillAudit(skill.skill_id, False,
                              ("owner_or_reviewer_or_lane_gate_closed",))
        return result

    def active(self) -> list[str]:
        return sorted(self._skills)

    def review(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "enabled": self._enabled,
            "self_install": False,
            "active_skills": self.active(),
            "allowed_capabilities": sorted(self._allowed),
            "forbidden_risk": sorted(_FORBIDDEN_RISK),
        }


# --- Task Graph IR --------------------------------------------------------
@dataclass(frozen=True)
class TaskNode:
    node_id: str
    capability_id: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskGraph:
    nodes: tuple[TaskNode, ...] = ()

    def validate(self, *, allowed_capabilities: frozenset[str]) -> None:
        ids = [n.node_id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise SkillError("node_id duplicati nel task graph")
        idset = set(ids)
        for node in self.nodes:
            if node.capability_id not in allowed_capabilities:
                raise SkillError(f"capability non allowlistata: {node.capability_id}")
            for dep in node.depends_on:
                if dep not in idset:
                    raise SkillError(f"dipendenza inesistente: {dep}")
        self.topological_order()        # solleva se ci sono cicli

    def topological_order(self) -> list[str]:
        order: list[str] = []
        temp: set[str] = set()
        done: set[str] = set()
        by_id = {n.node_id: n for n in self.nodes}

        def visit(nid: str) -> None:
            if nid in done:
                return
            if nid in temp:
                raise SkillError("ciclo nel task graph")
            temp.add(nid)
            for dep in by_id[nid].depends_on:
                visit(dep)
            temp.discard(nid)
            done.add(nid)
            order.append(nid)

        for node in self.nodes:
            visit(node.node_id)
        return order


# --- delega a sub-agenti isolati ------------------------------------------
@dataclass(frozen=True)
class DelegationRequest:
    task_graph: TaskGraph
    isolation: str                 # worktree | container


@dataclass(frozen=True)
class DelegationDecision:
    allowed: bool
    blocked_reason: str | None
    reasons: tuple[str, ...]


def plan_delegation(request: DelegationRequest, *, enabled: bool = False,
                    owner_approved: bool = False,
                    isolation_available: bool = False,
                    allowed_capabilities: frozenset[str] = frozenset()) -> DelegationDecision:
    """Pianifica (non esegue) una delega a sub-agente isolato. D5 degrada chiuso:
    senza lane abilitata, isolamento disponibile e owner gate -> bloccato."""
    if not enabled:
        return DelegationDecision(False, "delegation_disabled", ("delegation_disabled",))
    if request.isolation not in _DELEGATION_ISOLATION:
        return DelegationDecision(False, "unknown_isolation", ("unknown_isolation",))
    if not isolation_available:
        return DelegationDecision(False, "isolation_backend_unavailable",
                                  ("isolation_backend_unavailable",))
    try:
        request.task_graph.validate(allowed_capabilities=allowed_capabilities)
    except SkillError as exc:
        return DelegationDecision(False, "invalid_task_graph", (str(exc),))
    if not owner_approved:
        return DelegationDecision(False, "owner_approval_required",
                                  ("owner_approval_required",))
    return DelegationDecision(True, None, ("delegation_planned",))


@dataclass(frozen=True)
class DelegationResult:
    ok: bool
    output: dict
    error: str | None
    backend: str


class IsolatedDelegator:
    """Execute a reviewed sub-agent entrypoint in an ephemeral isolated workspace."""

    def __init__(self, agent_script: Path, *, enabled: bool = False,
                 allowed_capabilities: tuple[str, ...] = (), audit=None):
        self.agent_script = Path(agent_script).resolve()
        self.enabled = bool(enabled)
        self.allowed = frozenset(allowed_capabilities)
        self.audit = audit or (lambda kind, payload: None)

    def execute(self, request: DelegationRequest, *, owner_approved: bool,
                repository: Path | None = None) -> DelegationResult:
        decision = plan_delegation(
            request, enabled=self.enabled, owner_approved=owner_approved,
            isolation_available=backend_available(
                "container" if request.isolation == "container" else "process"),
            allowed_capabilities=self.allowed)
        if not decision.allowed:
            return DelegationResult(False, {}, decision.blocked_reason, request.isolation)
        if not self.agent_script.is_file():
            return DelegationResult(False, {}, "agent_entrypoint_missing", request.isolation)

        root = Path(tempfile.mkdtemp(prefix="seed-delegate-"))
        worktree = root / "workspace"
        try:
            if request.isolation == "worktree" and repository is not None:
                repo = Path(repository).resolve()
                proc = subprocess.run(
                    ["git", "-C", str(repo), "worktree", "add", "--detach",
                     str(worktree), "HEAD"], capture_output=True, text=True, timeout=30)
                if proc.returncode != 0:
                    return DelegationResult(False, {}, "worktree_creation_failed",
                                            request.isolation)
            else:
                worktree.mkdir(parents=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "nodes": [
                    {"node_id": n.node_id, "capability_id": n.capability_id,
                     "depends_on": list(n.depends_on)}
                    for n in request.task_graph.nodes
                ],
                "order": request.task_graph.topological_order(),
                "allowed_capabilities": sorted(self.allowed),
            }
            result: IsolationResult = run_python(
                self.agent_script, payload, workspace=worktree,
                policy=IsolationPolicy(
                    backend="container" if request.isolation == "container" else "process",
                    timeout_seconds=120))
            self.audit("delegation_executed", {
                "schema_version": SCHEMA_VERSION, "ok": result.ok,
                "backend": result.backend, "nodes": len(request.task_graph.nodes)})
            return DelegationResult(result.ok, result.output,
                                    None if result.ok else result.stderr, result.backend)
        finally:
            if repository is not None and worktree.exists() and request.isolation == "worktree":
                subprocess.run(["git", "-C", str(Path(repository).resolve()), "worktree",
                                "remove", "--force", str(worktree)],
                               capture_output=True, timeout=30)
            shutil.rmtree(root, ignore_errors=True)


class CapabilityTaskAgent:
    """Real local sub-agent: executes a reviewed DAG, one isolated capability per node."""

    def __init__(self, registry, *, enabled: bool = False,
                 allowed_capabilities: tuple[str, ...] = (), audit=None):
        self.registry = registry
        self.enabled = bool(enabled)
        self.allowed = frozenset(allowed_capabilities)
        self.audit = audit or (lambda kind, payload: None)

    def execute(self, request: DelegationRequest, arguments: dict[str, dict], *,
                owner_approved: bool) -> DelegationResult:
        backend = "container" if request.isolation == "container" else "process"
        decision = plan_delegation(
            request, enabled=self.enabled, owner_approved=owner_approved,
            isolation_available=backend_available(backend),
            allowed_capabilities=self.allowed)
        if not decision.allowed:
            return DelegationResult(False, {}, decision.blocked_reason, backend)
        outputs: dict[str, dict] = {}
        for node_id in request.task_graph.topological_order():
            node = next(item for item in request.task_graph.nodes if item.node_id == node_id)
            cap = self.registry.get(node.capability_id)
            if cap is None or cap.state != "active":
                return DelegationResult(False, outputs, "capability_not_active", backend)
            if node.capability_id not in self.allowed:
                return DelegationResult(False, outputs, "capability_not_allowlisted", backend)
            result = sandbox.run_tool(
                cap.directory, arguments.get(node_id, {}),
                timeout=int(cap.manifest.get("timeout", 30)), backend=backend,
                network_allowed=bool(cap.manifest.get("needs_network")))
            if not result.ok:
                self.audit("delegation_node_failed", {
                    "node_id": node_id, "capability_id": node.capability_id,
                    "backend": backend})
                return DelegationResult(False, outputs, result.stderr, backend)
            outputs[node_id] = result.output
        self.audit("delegation_completed", {
            "nodes": len(outputs), "backend": backend})
        return DelegationResult(True, outputs, None, backend)
