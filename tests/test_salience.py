"""K3 salienza deterministica: context gate spiegabile, default silenzio."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import salience  # noqa: E402
from seed.core import forbidden  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.knowledge import KnowledgeStore, UserClaim  # noqa: E402
from seed.core.living_profile import LivingProfileBuilder  # noqa: E402
from seed.core.memory import Memory  # noqa: E402
from seed.core.telemetry import Telemetry  # noqa: E402


def _item(**overrides):
    base = {
        "statement": "progetto unreal engine",
        "kid": 1,
        "claim_type": "preference",
        "confidence": 0.9,
        "provenance": [10, 11],
        "sensitivity": "normal",
        "lifecycle_state": "active",
        "superseded_at": None,
        "created_at": time.time(),
    }
    base.update(overrides)
    return base


def test_relevant_item_enters_with_stable_reasons():
    item = _item()
    first = salience.score_item("parliamo del progetto unreal", item,
                                item_ref="knowledge:1", now=1000)
    second = salience.score_item("parliamo del progetto unreal", item,
                                 item_ref="knowledge:1", now=1000)
    assert first == second
    assert first.action == "use_context"
    assert any(reason.startswith("relevance=") for reason in first.reasons)


def test_unrelated_item_remains_silent_no_dump():
    selected, decisions = salience.select_context(
        "che tempo fa domani", [_item()])
    assert selected == []
    assert decisions[0].action == "remember_silently"


def test_sensitive_candidate_stale_and_contradicted_are_silent():
    query = "dimmi del progetto unreal"
    cases = [
        _item(sensitivity="sensitive"),
        _item(lifecycle_state="candidate"),
        _item(lifecycle_state="superseded", superseded_at=1),
    ]
    for item in cases:
        assert salience.score_item(
            query, item, item_ref="knowledge:1").action == "remember_silently"
    contradicted = salience.score_item(
        query, _item(), item_ref="knowledge:1",
        edges=[{"source_id": 1, "target_id": 2,
                "edge_type": "contradicts", "weight": 1.0}])
    assert contradicted.action == "remember_silently"


def test_graph_connected_item_can_enter_with_explainable_seed():
    seed = _item(kid=1)
    connected = _item(kid=2, statement="motore grafico avanzato")
    selected, decisions = salience.select_context(
        "parliamo del progetto unreal", [seed, connected],
        edges=[{"source_id": 1, "target_id": 2,
                "edge_type": "supports", "weight": 1.0}])
    assert {item["kid"] for item in selected} == {1, 2}
    assert decisions[1].factors["relevance"] == 0.55


def test_recurrence_and_confidence_raise_score():
    weak = salience.score_item(
        "progetto unreal", _item(confidence=0.2, provenance=[]),
        item_ref="knowledge:1")
    strong = salience.score_item(
        "progetto unreal", _item(confidence=0.9, provenance=[1, 2, 3]),
        item_ref="knowledge:1")
    assert strong.score > weak.score


def test_approved_profile_filtered_to_salient_claim_ids(tmp_path):
    memory = Memory(tmp_path / "salience.db")
    store = KnowledgeStore(memory)
    first = store.record(UserClaim("preference", "progetto", "Unreal"))
    store.record(UserClaim("relation", "residenza", "Roma"))
    builder = LivingProfileBuilder(memory)
    builder.rebuild()
    profile = memory.latest_living_profile()
    memory.set_living_profile_review(profile["version"], "approved")

    sections, _ = builder.approved_context(source_claim_ids={first["id"]})
    dump = json.dumps(sections)
    assert "Unreal" in dump
    assert "Roma" not in dump


def test_counterpoint_filtered_by_query():
    fragments = [
        {"topic": "ritmo lavoro", "reason": "forse lavora di notte"},
        {"topic": "sport", "reason": "forse segue calcio"},
    ]
    selected = salience.select_counterpoint("parliamo del ritmo di lavoro", fragments)
    assert selected == [fragments[0]]


def test_seed_prompt_uses_relevant_memory_without_dumping_unrelated(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    app = SeedApp(SeedConfig())
    app.memory.add_fact("progetto personale usa Unreal Engine", 0.9, [1, 2])

    unrelated = app._system_prompt(
        app.personality.plan("che tempo fa domani"), "che tempo fa domani")
    relevant = app._system_prompt(
        app.personality.plan("parliamo del progetto Unreal"),
        "parliamo del progetto Unreal")

    assert "progetto personale usa Unreal Engine" not in unrelated
    assert "progetto personale usa Unreal Engine" in relevant
    assert {
        row["action"] for row in app.memory.salience_decisions()
    } == {"use_context"}
    app.shutdown()


def test_salience_telemetry_is_aggregate_only(tmp_path):
    memory = Memory(tmp_path / "salience-report.db")
    memory.add_salience_decision(
        item_ref="knowledge:7", action="use_context", score=0.8,
        reasons=["relevance=1.00"], factors={"relevance": 1.0})

    class EvolutionStub:
        versions_dir = tmp_path / "versions"

        @staticmethod
        def user_model():
            return {}

    report = Telemetry(memory, EvolutionStub()).build_report()
    serialized = json.dumps(report["salience"], ensure_ascii=False)

    assert report["salience"] == {
        "decisions": 1, "by_action": {"use_context": 1}}
    assert "knowledge:7" not in serialized
    assert "relevance" not in serialized
