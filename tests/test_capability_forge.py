"""P7.0 Selective Capability Forge — fondazione: contratti V2, lifecycle FSM,
authority subset fail-closed, secret discard, migrazione V1 conservativa.
Nessun runtime; default OFF."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core import capability_forge as cf  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402


# --- lifecycle FSM ---------------------------------------------------------
def test_valid_lifecycle_path():
    state = "observed"
    for nxt in ("framed", "researching", "planned", "building", "evaluating",
                "shadow", "canary", "active", "dormant"):
        state = cf.advance_lifecycle(state, nxt)
    assert state == "dormant"


def test_invalid_transition_fails_closed():
    with pytest.raises(cf.LifecycleError):
        cf.advance_lifecycle("observed", "active")     # salto di gate vietato
    with pytest.raises(cf.LifecycleError):
        cf.advance_lifecycle("active", "building")      # indietro non ammesso


def test_unknown_state_fails_closed():
    assert cf.can_transition("ghost", "active") is False
    with pytest.raises(cf.LifecycleError):
        cf.advance_lifecycle("shadow", "teleport")


def test_terminal_states_have_no_exits():
    assert cf.can_transition("rejected", "active") is False
    assert cf.can_transition("archived", "active") is False


def test_quarantine_reachable_from_active():
    assert cf.advance_lifecycle("active", "quarantined") == "quarantined"


# --- secret discard --------------------------------------------------------
def test_discard_secret_keys_and_nested():
    payload = {"user": "ada", "password": "x", "config": {"api_key": "k", "host": "h"},
               "note": "ok"}
    clean, n = cf.discard_secrets(payload)
    assert n == 2
    assert "password" not in clean and "api_key" not in clean["config"]
    assert clean["user"] == "ada" and clean["config"]["host"] == "h" and clean["note"] == "ok"


def test_discard_secret_value_shapes():
    assert cf.looks_like_secret(value="eyJhbGciOiJIUzI1NiIixxxxxxxxxx")   # jwt-like
    assert cf.looks_like_secret(value="Bearer abc.def.ghi")
    assert cf.looks_like_secret(value="sk-ABCDEFGHIJKLMNOPQRST")
    assert not cf.looks_like_secret(key="city", value="Roma")


def test_discard_keeps_non_secrets():
    clean, n = cf.discard_secrets({"topic": "meteo", "count": 3})
    assert n == 0 and clean == {"topic": "meteo", "count": 3}


# --- authority subset (fail-closed) ----------------------------------------
def _env(**kw):
    base = dict(authority_id="a", connection_id="conn1",
                data_classes=frozenset({"email_meta"}), effects=frozenset({"read"}),
                scopes=frozenset({"inbox"}), destinations=frozenset({"local"}),
                schedules=frozenset({"daily"}), quantitative_limits={"max_items": 50})
    base.update(kw)
    return cf.AuthorityEnvelope(**base)


def test_equal_authority_is_within():
    v = cf.authority_subset(_env(), _env())
    assert v["within_authority"] is True


def test_extra_data_class_is_escalation():
    req = _env(data_classes=frozenset({"email_meta", "email_body"}))
    v = cf.authority_subset(req, _env())
    assert v["within_authority"] is False and "data_classes" in v["escalations"]


def test_extra_effect_is_escalation():
    req = _env(effects=frozenset({"read", "send"}))
    v = cf.authority_subset(req, _env())
    assert v["within_authority"] is False and "effects" in v["escalations"]


def test_limit_exceeded_and_unknown_fail_closed():
    over = cf.authority_subset(_env(quantitative_limits={"max_items": 100}), _env())
    assert over["within_authority"] is False and "limit:max_items:exceeded" in over["escalations"]
    unknown = cf.authority_subset(_env(quantitative_limits={"max_sends": 1}), _env())
    assert unknown["within_authority"] is False and "limit:max_sends:unknown" in unknown["escalations"]


def test_connection_mismatch_is_escalation():
    v = cf.authority_subset(_env(connection_id="other"), _env())
    assert v["within_authority"] is False and "connection" in v["escalations"]


def test_expiry_beyond_granted_is_escalation():
    v = cf.authority_subset(_env(expires_at=200.0), _env(expires_at=100.0))
    assert v["within_authority"] is False and "expiry" in v["escalations"]


def test_subset_strictly_smaller_is_within():
    req = _env(data_classes=frozenset(), effects=frozenset({"read"}),
               scopes=frozenset(), destinations=frozenset({"local"}),
               schedules=frozenset(), quantitative_limits={})
    assert cf.authority_subset(req, _env())["within_authority"] is True


def test_malformed_envelope_fails_closed():
    bad = cf.AuthorityEnvelope(connection_id="conn1", data_classes=["not_a_set"])
    v = cf.authority_subset(bad, _env())
    assert v["within_authority"] is False and "malformed" in v["escalations"]


# --- contratti -------------------------------------------------------------
def test_workflow_evidence_sensitive_cannot_retain_raw():
    cf.WorkflowEvidence(evidence_id="e", source_kind="app", activity_kind="x").validate()
    with pytest.raises(cf.ForgeError):
        cf.WorkflowEvidence(evidence_id="e", source_kind="app", activity_kind="x",
                            sensitivity="sensitive", raw_retention="consented").validate()


def test_need_hypothesis_uncertainty_range():
    with pytest.raises(cf.ForgeError):
        cf.NeedHypothesis(hypothesis_id="h", user_goal="g", observed_problem="p",
                          uncertainty=2.0).validate()


def test_fitness_hard_blocker_cannot_be_compensated():
    with pytest.raises(cf.ForgeError):
        cf.FitnessDecision(decision_id="d", need_hypothesis_ref="h",
                           hard_blockers=("privacy",), verdict="build").validate()
    cf.FitnessDecision(decision_id="d", need_hypothesis_ref="h",
                       hard_blockers=("privacy",), verdict="do_nothing").validate()


def test_connector_kind_and_pinning():
    with pytest.raises(cf.ForgeError):
        cf.ConnectorDescriptor(connector_id="c", kind="telepathy").validate()
    with pytest.raises(cf.ForgeError):
        cf.ConnectorDescriptor(connector_id="c", kind="mcp_remote").validate()   # no digest
    cf.ConnectorDescriptor(connector_id="c", kind="mcp_remote", digest="abc123").validate()


def test_connection_requirement_human_and_revocation():
    with pytest.raises(cf.ForgeError):
        cf.ConnectionRequirement(connection_id="c", human_reason="").validate()
    cf.ConnectionRequirement(connection_id="c", human_reason="leggere le email",
                             revocation_path="impostazioni").validate()


def test_capability_plan_requires_rollback_and_valid_authority():
    plan = cf.CapabilityPlan(capability_id="cap", need_hypothesis_ref="h",
                             selected_connector_ref="c",
                             requested_authority=_env(), rollback_plan="ripristina")
    plan.validate()
    with pytest.raises(cf.ForgeError):
        cf.CapabilityPlan(capability_id="cap", need_hypothesis_ref="h",
                          selected_connector_ref="c",
                          requested_authority=_env(), rollback_plan="").validate()


def test_eval_report_pass_incompatible_with_blockers():
    with pytest.raises(cf.ForgeError):
        cf.CapabilityEvaluationReport(capability_id="cap", manifest_digest="d",
                                      verdict="pass", blockers=("ssrf",)).validate()
    rep = cf.CapabilityEvaluationReport(capability_id="cap", manifest_digest="d",
                                        verdict="pass")
    rep.validate()
    assert rep.passed is True


# --- migrazione V1 conservativa --------------------------------------------
def test_v1_migration_is_conservative_no_auto_activation():
    m = cf.migrate_v1_capability({"capability_id": "legacy.tool", "description": "x",
                                  "risk_class": "safe"})
    assert m.auto_activation is False
    assert m.requested_authority == cf.AuthorityEnvelope()    # nessuna autorita'
    assert m.provenance == "migrated_v1"


def test_v1_migration_requires_id():
    with pytest.raises(cf.ForgeError):
        cf.migrate_v1_capability({"description": "x"})


# --- config default OFF + nessuna primitiva runtime ------------------------
def test_capability_forge_off_by_default():
    cfg = SeedConfig()
    assert cfg.capability_forge.enabled is False
    assert cfg.capability_forge.auto_activation_enabled is False


def test_module_is_pure_no_network_exec_imports():
    import ast

    tree = ast.parse(inspect.getsource(cf))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    for forbidden in ("requests", "urllib", "socket", "subprocess", "os", "http"):
        assert forbidden not in modules
