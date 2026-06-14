"""Test S10.5 shadow review su candidate sintetiche + owner gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import shadow_review  # noqa: E402
from seed.core.design_review import DesignReviewer  # noqa: E402
from seed.core.directive_pack import build_directive_pack  # noqa: E402
from seed.core.lineage import LineageStore  # noqa: E402
from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.model_router import ModelRouter  # noqa: E402


class TrackingClient:
    has_key = True

    def __init__(self, text):
        self.text = text
        self.calls = 0

    def chat(self, messages, *, model=None, **kw):
        self.calls += 1
        return LLMResponse(text=self.text, usage={"total_tokens": 5})


def _router(client):
    return ModelRouter(client, {"design_reviewer": "gpt-oss"})


def _pass_client():
    return TrackingClient(json.dumps({"verdict": "pass", "violations": []}))


# -- shadow su candidate sintetiche -----------------------------------------

def test_synthetic_candidates_has_clean_and_risky():
    cands = shadow_review.synthetic_candidates()
    ids = {c[0] for c in cands}
    assert ids == {"shadow-clean", "shadow-permission"}


def test_run_shadow_review_reviews_all_synthetic(tmp_path):
    lineage = LineageStore(tmp_path / "lineage")
    reviewer = DesignReviewer(lineage=lineage, reviews_root=tmp_path / "rev")
    digest = shadow_review.run_shadow_review(reviewer, _router(_pass_client()))
    assert digest["reviewed"] == 2 and digest["shadow"] is True
    # evidenza registrata, marcata shadow, nessuna promozione
    events = lineage.events()
    assert [e["event_type"] for e in events] == ["design_review_recorded"] * 2
    assert all(e["payload"]["shadow"] is True for e in events)
    assert all(e["event_type"] != "promotion_decision" for e in events)


def test_shadow_review_does_not_require_owner_gate(tmp_path):
    # shadow gira anche con owner gate chiuso (real_enabled=False default)
    reviewer = DesignReviewer()
    digest = shadow_review.run_shadow_review(reviewer, _router(_pass_client()))
    assert digest["verdicts"].get("pass") == 2


# -- owner gate su candidate reali ------------------------------------------

def _pack():
    return build_directive_pack(feature="S10.5", scope="policy_change",
                                candidate={"manifest": {"mutation_id": "real-1"},
                                           "diff": "x"})


def test_real_review_blocked_without_owner_gate():
    client = _pass_client()
    reviewer = DesignReviewer(real_enabled=False)
    res = reviewer.review(_pack(), _router(client), candidate_id="real-1", shadow=False)
    assert res.verdict == "inconclusive"
    assert any("owner gate" in m for m in res.missing_evidence)
    assert client.calls == 0                # provider mai chiamato


def test_real_review_runs_when_owner_enables():
    client = _pass_client()
    reviewer = DesignReviewer(real_enabled=True)
    res = reviewer.review(_pack(), _router(client), candidate_id="real-1", shadow=False)
    assert res.verdict == "pass"
    assert client.calls == 1
