"""Test S10.3 Design Reviewer: read-only, schema-validato localmente, evidenza
nel lineage, fail-closed su output invalido/incoerente (mai falso pass)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.design_review import DesignReviewer  # noqa: E402
from seed.core.directive_pack import build_directive_pack  # noqa: E402
from seed.core.lineage import LineageStore  # noqa: E402
from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.model_router import ModelRouter  # noqa: E402

_CANDIDATE = {"manifest": {"mutation_id": "cand-1"}, "diff": "x.json: +1"}


def _pack():
    return build_directive_pack(feature="S10", scope="policy_change",
                                candidate=_CANDIDATE)


class CannedClient:
    """Ritorna sempre lo stesso testo; opzionalmente fallisce o e' senza key."""

    def __init__(self, text="", has_key=True, fail=False):
        self.text = text
        self.has_key = has_key
        self.fail = fail

    def chat(self, messages, *, model=None, **kw):
        if self.fail:
            raise RuntimeError("provider down")
        return LLMResponse(text=self.text, usage={"total_tokens": 7})


def _router(client, model="gpt-oss"):
    return ModelRouter(client, {"design_reviewer": model})


def _events():
    captured = []
    return captured, lambda ev, p: captured.append((ev, p))


# -- configurazione ---------------------------------------------------------

def test_unconfigured_reviewer_is_inconclusive():
    r = ModelRouter(CannedClient(has_key=False), {"design_reviewer": "gpt-oss"})
    res = DesignReviewer().review(_pack(), r, candidate_id="cand-1")
    assert res.verdict == "inconclusive"


def test_no_model_for_role_is_inconclusive():
    r = ModelRouter(CannedClient(), {})   # reviewer non mappato
    res = DesignReviewer().review(_pack(), r, candidate_id="cand-1")
    assert res.verdict == "inconclusive"


# -- verdetti validi --------------------------------------------------------

def test_valid_pass_no_violations():
    client = CannedClient(json.dumps({"verdict": "pass", "violations": []}))
    res = DesignReviewer().review(_pack(), _router(client), candidate_id="cand-1")
    assert res.verdict == "pass"
    assert res.violations == []
    assert res.model == "gpt-oss"


def test_valid_fail_with_known_violation():
    client = CannedClient(json.dumps({"verdict": "fail", "violations": [
        {"directive_id": "privacy.remote_payload_minimal", "severity": "blocking",
         "evidence_ref": "diff:x.json:1", "reason": "payload non redatto"}]}))
    res = DesignReviewer().review(_pack(), _router(client), candidate_id="cand-1")
    assert res.verdict == "fail"
    assert res.blocking == 1


# -- fail-closed: output invalido o incoerente -> inconclusive --------------

def test_non_json_output_is_inconclusive():
    res = DesignReviewer().review(_pack(), _router(CannedClient("non sono json")),
                                  candidate_id="cand-1")
    assert res.verdict == "inconclusive"


def test_missing_verdict_is_inconclusive():
    client = CannedClient(json.dumps({"violations": []}))
    res = DesignReviewer().review(_pack(), _router(client), candidate_id="cand-1")
    assert res.verdict == "inconclusive"


def test_pass_with_blocking_violation_is_inconclusive():
    client = CannedClient(json.dumps({"verdict": "pass", "violations": [
        {"directive_id": "recovery.no_inplace_overwrite", "severity": "blocking"}]}))
    res = DesignReviewer().review(_pack(), _router(client), candidate_id="cand-1")
    assert res.verdict == "inconclusive"


def test_fail_without_violations_is_inconclusive():
    client = CannedClient(json.dumps({"verdict": "fail", "violations": []}))
    res = DesignReviewer().review(_pack(), _router(client), candidate_id="cand-1")
    assert res.verdict == "inconclusive"


def test_unknown_directive_id_is_inconclusive():
    client = CannedClient(json.dumps({"verdict": "fail", "violations": [
        {"directive_id": "non.esiste", "severity": "high"}]}))
    res = DesignReviewer().review(_pack(), _router(client), candidate_id="cand-1")
    assert res.verdict == "inconclusive"

def test_ui_directive_id_is_valid_for_ui_pack():
    pack = build_directive_pack(feature="UI", scope="ui_change",
                                candidate=_CANDIDATE)
    client = CannedClient(json.dumps({"verdict": "fail", "violations": [
        {"directive_id": "ui.e_02", "severity": "blocking"}]}))
    res = DesignReviewer().review(pack, _router(client), candidate_id="cand-1")
    assert res.verdict == "fail"


def test_ui_p0_violation_is_blocked_before_llm():
    pack = build_directive_pack(
        feature="UI", scope="ui_change",
        candidate={**_CANDIDATE,
                   "ui_violated_precedence": ["P0_control_safety"]})
    res = DesignReviewer().review(
        pack, _router(CannedClient(fail=True)), candidate_id="cand-1")
    assert res.verdict == "fail"
    assert res.model == "deterministic-ui-gate"
    assert res.blocking == 1


def test_provider_error_is_inconclusive():
    res = DesignReviewer().review(_pack(), _router(CannedClient(fail=True)),
                                  candidate_id="cand-1")
    assert res.verdict == "inconclusive"


# -- evidenza: lineage + audit + file, mai promotion ------------------------

def test_review_recorded_as_lineage_evidence_and_audit(tmp_path):
    lineage = LineageStore(tmp_path / "lineage")
    events, audit = _events()
    client = CannedClient(json.dumps({"verdict": "pass", "violations": []}))
    reviewer = DesignReviewer(lineage=lineage, reviews_root=tmp_path / "reviews",
                              audit=audit)
    reviewer.review(_pack(), _router(client), candidate_id="cand-1")

    types = [e["event_type"] for e in lineage.events()]
    assert types == ["design_review_recorded"]          # solo evidenza, nessuna transizione
    assert lineage.events()[0]["payload"]["verdict"] == "pass"
    assert ("design_review", {"verdict": "pass", "model": "gpt-oss",
                              "violations": 0, "blocking": 0, "shadow": True}) in events
    assert (tmp_path / "reviews" / "cand-1.json").exists()


def test_reviewer_does_not_promote_or_transition(tmp_path):
    lineage = LineageStore(tmp_path / "lineage")
    client = CannedClient(json.dumps({"verdict": "fail", "violations": [
        {"directive_id": "authority.generator_cannot_self_promote",
         "severity": "blocking"}]}))
    DesignReviewer(lineage=lineage).review(
        _pack(), _router(client), candidate_id="cand-1")
    types = {e["event_type"] for e in lineage.events()}
    assert types == {"design_review_recorded"}
    assert "promotion_decision" not in types
    assert "status_transition" not in types
