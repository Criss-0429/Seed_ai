"""P7.1-P7.9 Selective Capability Forge: evidence, fitness, connector vetting,
builder V2, evaluator, connection broker/vault, activation authority, maintenance,
e bridge runtime. Engine puri + iniettati; default OFF; fail-closed."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core import capability_forge as cf  # noqa: E402
from seed.core import forge_runtime as fr  # noqa: E402
from seed.core import forge_connection as fc  # noqa: E402
from seed.core import forbidden  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402


# --- P7.1 Evidence Engine --------------------------------------------------
def test_evidence_requires_consent_and_discards_secrets():
    events = []
    eng = fr.EvidenceEngine(audit=lambda k, p: events.append((k, p)))
    assert eng.observe("mail", "triage", {"password": "x"}) is None     # no consent
    eng.grant("mail")
    ev = eng.observe("mail", "triage", {"subject_count": 12, "api_key": "sk-AAAAAAAAAAAAAAAA"})
    assert ev is not None and ev.raw_retention == "ephemeral"
    discarded = [p["secrets_discarded"] for k, p in events if k == "forge_evidence"][-1]
    assert discarded == 1


def test_evidence_sensitive_classified_and_no_local_path_fails_closed():
    eng = fr.EvidenceEngine()
    eng.grant("health_app")
    ev = eng.observe("health_app", "log", {"diagnosi": "x"})
    assert ev.sensitivity == "sensitive"
    assert eng.observe("health_app", "log", {"a": 1}, has_local_safe_path=False) is None


def test_evidence_revoke_purges():
    eng = fr.EvidenceEngine()
    eng.grant("mail")
    eng.observe("mail", "triage", {"a": 1})
    assert len(eng.evidence()) == 1
    assert eng.revoke("mail") == 1 and eng.evidence() == []


# --- P7.2 Need & Fitness ---------------------------------------------------
def _evidences(n, sensitivity="normal"):
    out = []
    for i in range(n):
        out.append(cf.WorkflowEvidence(evidence_id=f"e{i}", source_kind="mail",
                   activity_kind="triage", recurrence=1, sensitivity=sensitivity))
    return out


def test_need_below_threshold_is_not_framed():
    eng = fr.NeedFitnessEngine()
    assert eng.frame_need(_evidences(2), user_goal="g", observed_problem="p",
                          sessions=1) is None


def test_need_framed_when_threshold_met_and_explicit_bypasses_recurrence():
    eng = fr.NeedFitnessEngine()
    h = eng.frame_need(_evidences(3), user_goal="g", observed_problem="p", sessions=2)
    assert h is not None
    h2 = eng.frame_need(_evidences(1), user_goal="g2", observed_problem="p",
                        sessions=1, explicit=True)
    assert h2 is not None


def test_sensitive_need_requires_higher_threshold():
    eng = fr.NeedFitnessEngine()
    assert eng.frame_need(_evidences(3, "sensitive"), user_goal="g",
                          observed_problem="p", sessions=2) is None   # 3<5
    assert eng.frame_need(_evidences(5, "sensitive"), user_goal="g",
                          observed_problem="p", sessions=3) is not None


def test_suppressed_need_blocked():
    eng = fr.NeedFitnessEngine()
    eng.suppress("g", until=100.0)
    assert eng.frame_need(_evidences(9), user_goal="g", observed_problem="p",
                          sessions=5, now=50.0) is None


def _need():
    return cf.NeedHypothesis(hypothesis_id="h", user_goal="g", observed_problem="p")


def test_fitness_hard_blocker_forces_do_nothing():
    eng = fr.NeedFitnessEngine()
    d = eng.decide_fitness(_need(), alternatives=("build",), expected_utility=0.9,
                           privacy_cost=0.0, trust_cost=0.0, maintenance_cost=0.0,
                           operational_risk=0.0, hard_blockers=("privacy",))
    assert d.verdict == "do_nothing"


def test_fitness_prefers_simplest_and_respects_cost():
    eng = fr.NeedFitnessEngine()
    cheap = eng.decide_fitness(_need(), alternatives=("reuse", "build"),
                               expected_utility=0.9, privacy_cost=0.1, trust_cost=0.1,
                               maintenance_cost=0.1, operational_risk=0.1)
    assert cheap.verdict == "reuse"        # piu' semplice adeguato
    nope = eng.decide_fitness(_need(), alternatives=("build",), expected_utility=0.2,
                              privacy_cost=0.3, trust_cost=0.2, maintenance_cost=0.2,
                              operational_risk=0.2)
    assert nope.verdict == "do_nothing"    # valore non supera il costo


def test_two_synthetic_users_diverge_no_hardcoded_branch():
    eng = fr.NeedFitnessEngine()
    a = eng.decide_fitness(_need(), alternatives=("reuse",), expected_utility=0.8,
                           privacy_cost=0.1, trust_cost=0.1, maintenance_cost=0.0,
                           operational_risk=0.0)
    b = eng.decide_fitness(_need(), alternatives=("build",), expected_utility=0.3,
                           privacy_cost=0.4, trust_cost=0.1, maintenance_cost=0.1,
                           operational_risk=0.1)
    assert a.verdict == "reuse" and b.verdict == "do_nothing"     # esiti diversi


# --- P7.3 Connector vetting -----------------------------------------------
def _conn(**kw):
    base = dict(connector_id="c1", kind="mcp_remote", digest="d1",
                tool_schema_hash="h1", destinations=("api.svc.com",))
    base.update(kw)
    return cf.ConnectorDescriptor(**base)


def test_vet_blocks_non_allowlisted_destination_ssrf():
    v = fr.ConnectorVetter(allowed_destinations=frozenset({"safe.com"}))
    out = v.vet(_conn())
    assert out["verification_state"] == "blocked"
    assert "destinations_not_allowlisted" in out["blocking"]


def test_vet_blocks_scan_findings():
    v = fr.ConnectorVetter(allowed_destinations=frozenset({"api.svc.com"}))
    out = v.vet(_conn(), scan=lambda d: ["token_passthrough", "excessive_scope"])
    assert out["verification_state"] == "blocked"
    assert "scan:token_passthrough" in out["blocking"]


def test_vet_verifies_clean_and_detects_drift():
    v = fr.ConnectorVetter(allowed_destinations=frozenset({"api.svc.com"}))
    assert v.vet(_conn(), scan=lambda d: [])["verification_state"] == "verified"
    drift = v.check_drift(_conn(digest="d2"))
    assert drift["drift"] is True and drift["quarantine"] is True


# --- P7.4 Builder V2 -------------------------------------------------------
def _plan():
    return cf.CapabilityPlan(capability_id="cap.x", need_hypothesis_ref="h",
                             selected_connector_ref="c1",
                             requested_authority=cf.AuthorityEnvelope(connection_id="conn1"),
                             input_schema={"q": "str"}, output_schema={"r": "str"},
                             rollback_plan="restore")


def test_builder_produces_manifest_no_auto_activation():
    m = fr.CapabilityBuilderV2().build(_plan(), connector=_conn(dependency_lock_ref="lock1"))
    assert m.auto_activation is False and m.build_digest
    assert m.dependency_lock_ref == "lock1"


def test_builder_rejects_secret_in_schema():
    plan = cf.CapabilityPlan(capability_id="cap.x", need_hypothesis_ref="h",
                             selected_connector_ref="c1",
                             requested_authority=cf.AuthorityEnvelope(),
                             input_schema={"api_key": "str"}, rollback_plan="r")
    with pytest.raises(cf.ForgeError):
        fr.CapabilityBuilderV2().build(plan, connector=_conn())


def test_builder_has_no_promotion_or_vault_surface():
    b = fr.CapabilityBuilderV2()
    for attr in ("vault", "activation", "promote", "promotion"):
        assert not hasattr(b, attr)


# --- P7.5 Evaluator --------------------------------------------------------
def _manifest():
    return fr.CapabilityBuilderV2().build(_plan(), connector=_conn())


def test_evaluator_pass_only_when_all_checks_green():
    checks = {k: True for k in ("deterministic", "adversarial", "privacy",
                                "authority", "runtime")}
    rep = fr.IndependentEvaluator().evaluate(_manifest(), checks=checks)
    assert rep.verdict == "pass" and rep.passed


def test_evaluator_missing_check_is_inconclusive_not_approved():
    checks = {"deterministic": True}
    rep = fr.IndependentEvaluator().evaluate(_manifest(), checks=checks)
    assert rep.verdict == "inconclusive" and not rep.passed


def test_evaluator_blocker_blocks():
    checks = {k: True for k in ("deterministic", "adversarial", "privacy",
                                "authority", "runtime")}
    rep = fr.IndependentEvaluator().evaluate(_manifest(), checks=checks,
                                             blockers=("secret_exfil",))
    assert rep.verdict == "blocked"


# --- P7.6 Vault + Connection Broker ---------------------------------------
def test_vault_returns_handle_never_token():
    vault = fc.CredentialVault()
    handle = vault.put("conn1", "secret-token")
    assert "secret-token" not in handle
    assert vault.handle("conn1") == handle
    assert vault._resolve_token("conn1") == "secret-token"      # solo uso interno


def test_vault_expiry_and_revoke():
    vault = fc.CredentialVault()
    vault.put("conn1", "t", expires_at=time.time() - 1)
    assert vault.handle("conn1") is None                        # scaduto
    vault.put("conn2", "t")
    assert vault.revoke("conn2") is True and vault.handle("conn2") is None


def _req():
    return cf.ConnectionRequirement(connection_id="conn1",
                                    human_reason="leggere le email del mattino",
                                    allowed_effects=("read",), denied_effects=("send",),
                                    revocation_path="impostazioni")


def test_broker_describes_in_plain_language():
    broker = fc.ConnectionBroker(vault=fc.CredentialVault())
    desc = broker.describe(_req())
    assert "email" in desc and "token" not in desc.lower() and "oauth" not in desc.lower()


def test_broker_awaiting_without_reliable_or_complete_oauth():
    broker = fc.ConnectionBroker(vault=fc.CredentialVault())
    assert broker.connect(_req(), oauth_flow=None,
                          granted_authority=cf.AuthorityEnvelope())["state"] == "awaiting_connection"
    incomplete = broker.connect(_req(), oauth_flow=lambda r: {"access_token": "t"},
                                granted_authority=cf.AuthorityEnvelope())
    assert incomplete["state"] == "awaiting_connection"


def test_broker_connect_stores_token_returns_handle_not_token():
    broker = fc.ConnectionBroker(vault=fc.CredentialVault())

    def flow(r):
        return {"access_token": "secret", "code_verifier": "v",
                "state": "s", "audience": "a"}

    out = broker.connect(_req(), oauth_flow=flow, granted_authority=cf.AuthorityEnvelope())
    assert out["state"] == "connected" and "secret" not in str(out)
    assert broker.typed_handle("conn1") and "secret" not in str(broker.typed_handle("conn1"))


# --- P7.7 Activation Authority --------------------------------------------
def _passing_report(manifest):
    checks = {k: True for k in ("deterministic", "adversarial", "privacy",
                                "authority", "runtime")}
    return fr.IndependentEvaluator().evaluate(manifest, checks=checks)


def test_activation_awaiting_on_authority_escalation():
    m = _manifest()   # requested authority connection_id=conn1
    granted = cf.AuthorityEnvelope(connection_id="other")
    out = fc.ActivationAuthority(auto_activation_enabled=True).decide(
        report=_passing_report(m), manifest=m, granted_authority=granted,
        shadow_ok=True, canary_ok=True)
    assert out["state"] == "awaiting_connection" and not out["auto_activated"]


def test_activation_irreversible_never_auto():
    m = _manifest()
    granted = m.requested_authority
    out = fc.ActivationAuthority(auto_activation_enabled=True).decide(
        report=_passing_report(m), manifest=m, granted_authority=granted,
        shadow_ok=True, canary_ok=True, has_irreversible=True)
    assert out["auto_activated"] is False and "irreversible" in out["reason"]


def test_activation_blocked_when_shadow_or_eval_not_green():
    m = _manifest()
    out = fc.ActivationAuthority(auto_activation_enabled=True).decide(
        report=_passing_report(m), manifest=m, granted_authority=m.requested_authority,
        shadow_ok=False, canary_ok=True)
    assert out["auto_activated"] is False and "shadow_not_green" in out["blockers"]


def test_activation_within_authority_all_green():
    m = _manifest()
    auth = fc.ActivationAuthority(auto_activation_enabled=True)
    out = auth.decide(report=_passing_report(m), manifest=m,
                      granted_authority=m.requested_authority,
                      shadow_ok=True, canary_ok=True)
    assert out["state"] == "active" and out["auto_activated"] is True
    # con auto-attivazione OFF resta canary (mai auto)
    off = fc.ActivationAuthority(auto_activation_enabled=False).decide(
        report=_passing_report(m), manifest=m, granted_authority=m.requested_authority,
        shadow_ok=True, canary_ok=True)
    assert off["state"] == "canary" and off["auto_activated"] is False


def test_activation_irreversible_confirmation():
    auth = fc.ActivationAuthority()
    assert auth.confirm_irreversible(owner_confirmed=False)["allowed"] is False
    assert auth.confirm_irreversible(owner_confirmed=True)["allowed"] is True


# --- P7.9 Maintenance ------------------------------------------------------
def test_maintenance_quarantine_on_authority_drift():
    mon = fr.MaintenanceMonitor()
    out = mon.record_outcome("cap", expected="ok", observed="ok", authority_changed=True)
    assert out["state"] == "quarantined"


def test_maintenance_dormant_on_degraded_reliability():
    mon = fr.MaintenanceMonitor()
    mon.record_outcome("cap", expected="ok", observed="bad")
    out = mon.record_outcome("cap", expected="ok", observed="bad")
    assert out["state"] == "dormant"
    assert mon.reliability("cap") < 0.5


# --- P7.8 orchestrator + app bridge (gated, default OFF) -------------------
def _app(tmp_path, monkeypatch, *, enabled=False):
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    cfg = SeedConfig()
    cfg.capability_forge.enabled = enabled
    return SeedApp(cfg)


def test_app_forge_off_by_default(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, enabled=False)
    try:
        st = app.ui_forge_status()
        assert st["enabled"] is False
        assert app.ui_forge_grant_observation("mail")["reason"] == "forge_disabled"
    finally:
        app.memory.close()


def test_app_forge_enabled_observation_and_timeline(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, enabled=True)
    try:
        assert app.ui_forge_status()["enabled"] is True
        assert app.ui_forge_grant_observation("mail")["ok"] is True
        assert app.ui_forge_timeline() == []
        app.forge.record_decision(capability_id="cap.summary", state="do_nothing",
                                  why="evidenza insufficiente")
        tl = app.ui_forge_timeline()
        assert tl and tl[0]["state"] == "do_nothing"
        app.forge.evidence.observe("mail", "triage", {"a": 1})
        assert app.ui_forge_forget_source("mail")["purged"] == 1
    finally:
        app.memory.close()
