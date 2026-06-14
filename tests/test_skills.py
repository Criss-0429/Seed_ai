"""D5 skills + delega: audit, no self-install (owner gate), task graph IR
(no cicli, capability allowlistate), delega gated."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core.skills import (  # noqa: E402
    DelegationRequest, Skill, SkillError, SkillRegistry, SkillStep, TaskGraph,
    TaskNode, audit_skill, plan_delegation,
)

_ALLOWED = frozenset({"worker.runtime_status", "worker.write_workspace_note"})


def _skill(**kw):
    base = dict(skill_id="s1", description="",
                steps=(SkillStep("worker.runtime_status"),), risk_class="read_safe")
    base.update(kw)
    return Skill(**base)


# --- skill validation + audit ---------------------------------------------
def test_skill_validate_rejects_destructive():
    with pytest.raises(SkillError):
        _skill(risk_class="destructive").validate()


def test_audit_flags_non_allowlisted_capability():
    bad = _skill(steps=(SkillStep("worker.delete_everything"),))
    result = audit_skill(bad, allowed_capabilities=_ALLOWED)
    assert not result.passed
    assert any("non allowlistata" in v for v in result.violations)


def test_audit_passes_for_allowlisted():
    result = audit_skill(_skill(), allowed_capabilities=_ALLOWED)
    assert result.passed


# --- registry: no self-install, owner gate --------------------------------
def test_install_requires_owner_and_reviewer_and_enabled():
    reg = SkillRegistry(enabled=True, allowed_capabilities=tuple(_ALLOWED))
    # senza owner_approved -> non installa
    r1 = reg.install(_skill(), owner_approved=False, reviewer_passed=True)
    assert not r1.passed and reg.active() == []
    # senza reviewer -> non installa
    reg.install(_skill(), owner_approved=True, reviewer_passed=False)
    assert reg.active() == []
    # tutti i gate -> installa
    r2 = reg.install(_skill(), owner_approved=True, reviewer_passed=True)
    assert r2.passed and reg.active() == ["s1"]


def test_disabled_lane_blocks_install():
    reg = SkillRegistry(enabled=False, allowed_capabilities=tuple(_ALLOWED))
    reg.install(_skill(), owner_approved=True, reviewer_passed=True)
    assert reg.active() == []


def test_review_declares_no_self_install():
    reg = SkillRegistry(enabled=True)
    assert reg.review()["self_install"] is False


# --- task graph IR --------------------------------------------------------
def test_task_graph_topological_order():
    g = TaskGraph((
        TaskNode("a", "worker.runtime_status"),
        TaskNode("b", "worker.runtime_status", depends_on=("a",)),
    ))
    g.validate(allowed_capabilities=_ALLOWED)
    assert g.topological_order().index("a") < g.topological_order().index("b")


def test_task_graph_detects_cycle():
    g = TaskGraph((
        TaskNode("a", "worker.runtime_status", depends_on=("b",)),
        TaskNode("b", "worker.runtime_status", depends_on=("a",)),
    ))
    with pytest.raises(SkillError):
        g.validate(allowed_capabilities=_ALLOWED)


def test_task_graph_rejects_non_allowlisted_capability():
    g = TaskGraph((TaskNode("a", "worker.shell"),))
    with pytest.raises(SkillError):
        g.validate(allowed_capabilities=_ALLOWED)


def test_task_graph_rejects_missing_dependency():
    g = TaskGraph((TaskNode("a", "worker.runtime_status", depends_on=("ghost",)),))
    with pytest.raises(SkillError):
        g.validate(allowed_capabilities=_ALLOWED)


# --- delega gated ----------------------------------------------------------
def _req():
    return DelegationRequest(
        task_graph=TaskGraph((TaskNode("a", "worker.runtime_status"),)),
        isolation="worktree")


def test_delegation_disabled_by_default():
    d = plan_delegation(_req(), enabled=False)
    assert not d.allowed and d.blocked_reason == "delegation_disabled"


def test_delegation_blocked_without_isolation_backend():
    d = plan_delegation(_req(), enabled=True, owner_approved=True,
                        isolation_available=False, allowed_capabilities=_ALLOWED)
    assert not d.allowed and d.blocked_reason == "isolation_backend_unavailable"


def test_delegation_requires_owner_approval():
    d = plan_delegation(_req(), enabled=True, owner_approved=False,
                        isolation_available=True, allowed_capabilities=_ALLOWED)
    assert not d.allowed and d.blocked_reason == "owner_approval_required"


def test_delegation_planned_when_all_gates_open():
    d = plan_delegation(_req(), enabled=True, owner_approved=True,
                        isolation_available=True, allowed_capabilities=_ALLOWED)
    assert d.allowed and d.reasons == ("delegation_planned",)
