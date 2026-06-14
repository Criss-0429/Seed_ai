"""D-OBS observation lane READ-only: consenso per-classe, sensibile escluso,
salienza, candidate-only redatte, revoca+purge, audit aggregato."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core import observation as obs_mod  # noqa: E402
from seed.core.observation import (  # noqa: E402
    ObservationError, ObservationLane, ObservationSignal, decide_observation,
)
from seed.core.knowledge import KnowledgeStore  # noqa: E402
from seed.core.memory import Memory  # noqa: E402


def _signal(**kw):
    base = dict(obs_class="foreground_app", category="dev",
                redacted_ref="app:dev", salience=0.8, sensitive=False)
    base.update(kw)
    return ObservationSignal(**base)


def _lane(tmp_path, **kw):
    mem = Memory(tmp_path / "obs.db")
    store = KnowledgeStore(mem)
    lane = ObservationLane(mem, store, enabled=kw.pop("enabled", True), **kw)
    return lane, mem, store


# --- decisione deterministica ---------------------------------------------
def test_signal_validate_rejects_unredacted_secret():
    with pytest.raises(ObservationError):
        _signal(redacted_ref="ghp_0123456789abcdef0123456789abcdefABCD").validate()


def test_decide_discards_without_consent():
    d = decide_observation(_signal(), consent=frozenset())
    assert d.action == "discard" and d.reasons == ("class_not_consented",)


def test_decide_excludes_sensitive():
    d = decide_observation(_signal(category="health"),
                           consent=frozenset({"foreground_app"}))
    assert d.action == "discard" and d.reasons == ("sensitive_excluded",)


def test_decide_below_salience_remembers_silently():
    d = decide_observation(_signal(salience=0.2),
                           consent=frozenset({"foreground_app"}))
    assert d.action == "remember_silently"


def test_decide_salient_becomes_candidate():
    d = decide_observation(_signal(),
                           consent=frozenset({"foreground_app"}))
    assert d.action == "candidate"


# --- lane: default OFF + consenso -----------------------------------------
def test_lane_disabled_discards(tmp_path):
    lane, mem, _ = _lane(tmp_path, enabled=False)
    lane.set_consent("foreground_app", True)
    d = lane.observe(_signal())
    assert d.action == "discard" and d.reasons == ("lane_disabled",)
    mem.close()


def test_consent_default_off(tmp_path):
    lane, mem, _ = _lane(tmp_path)
    assert lane.consent() == frozenset()      # niente consentito di default
    d = lane.observe(_signal())
    assert d.action == "discard"
    mem.close()


def test_consented_salient_records_low_confidence_hypothesis(tmp_path):
    lane, mem, store = _lane(tmp_path)
    lane.set_consent("foreground_app", True)
    d = lane.observe(_signal())
    assert d.action == "candidate"
    rows = mem.all_knowledge()
    assert len(rows) == 1
    row = rows[0]
    assert row["claim_type"] == "hypothesis"
    assert row["lifecycle_state"] == "candidate"      # mai fatto
    assert row["confidence"] <= 0.45
    assert row["confidence_source"] == "inferred"
    mem.close()


# --- revoca + purge --------------------------------------------------------
def test_revoke_class_purges_its_candidates(tmp_path):
    lane, mem, _ = _lane(tmp_path)
    lane.set_consent("foreground_app", True)
    lane.observe(_signal())
    assert len(mem.all_knowledge()) == 1
    lane.set_consent("foreground_app", False)         # revoca classe -> purge
    assert mem.all_knowledge() == []
    assert lane.consent() == frozenset()
    mem.close()


def test_revoke_all_purges_and_disables(tmp_path):
    lane, mem, _ = _lane(tmp_path)
    lane.set_consent("foreground_app", True)
    lane.set_consent("process", True)
    lane.observe(_signal())
    lane.observe(_signal(obs_class="process", category="dev"))
    purged = lane.revoke_all()
    assert purged >= 1
    assert lane.consent() == frozenset()
    assert mem.all_knowledge() == []
    mem.close()


# --- audit aggregato + confini --------------------------------------------
def test_audit_is_aggregate_no_redacted_ref(tmp_path):
    events = []
    mem = Memory(tmp_path / "obs.db")
    lane = ObservationLane(mem, KnowledgeStore(mem), enabled=True,
                           audit=lambda k, p: events.append((k, p)))
    lane.set_consent("foreground_app", True)
    lane.observe(_signal(redacted_ref="app:dev"))
    blob = json.dumps(events)
    assert "app:dev" not in blob                       # ref mai nell'audit
    assert any(k == "observation_processed" for k, _ in events)
    mem.close()


def test_review_is_aggregate(tmp_path):
    lane, mem, _ = _lane(tmp_path)
    review = lane.review()
    assert review["read_only"] is True
    assert review["write_actions"] == 0
    assert review["consented_classes"] == []
    mem.close()


def test_module_has_no_action_primitives():
    src = inspect.getsource(obs_mod)
    assert "import subprocess" not in src
    assert "import os" not in src
