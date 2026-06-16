"""Test M1 selezione per rilevanza (recall.py): deterministica, solo pertinenti,
mai dump. + recent_chat per la persistenza cross-sessione."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden  # noqa: E402
from seed.core import recall  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.memory import Memory  # noqa: E402

_FACTS = [
    {"statement": "Preferisce risposte brevi durante il coding"},
    {"statement": "Sta seguendo un progetto chiamato Unreal Engine al lavoro"},
    {"statement": "Va in palestra il mercoledi sera"},
]


def test_selects_only_relevant_items():
    out = recall.select_relevant("dimmi del progetto unreal", _FACTS, k=8)
    assert len(out) == 1
    assert "Unreal" in out[0]["statement"]


def test_no_overlap_returns_empty_not_dump():
    out = recall.select_relevant("che tempo fa domani", _FACTS, k=8)
    assert out == []                       # niente di pertinente -> niente, non dump


def test_query_without_signal_returns_empty():
    assert recall.select_relevant("e", _FACTS) == []        # solo stopword/corte
    assert recall.select_relevant("", _FACTS) == []


def test_respects_k_limit():
    facts = [{"statement": f"nota sul progetto numero {i} progetto"} for i in range(20)]
    out = recall.select_relevant("progetto", facts, k=5)
    assert len(out) == 5


def test_recency_breaks_ties():
    now = time.time()
    items = [
        {"statement": "progetto vecchio", "created_at": now - 60 * 60 * 24 * 25},
        {"statement": "progetto nuovo", "created_at": now - 60},
    ]
    out = recall.select_relevant("progetto", items, k=2, now=now)
    assert out[0]["statement"] == "progetto nuovo"   # piu' recente prima a pari overlap


def test_explain_returns_matched_tokens():
    info = recall.explain("dimmi del progetto unreal", _FACTS[1])
    assert "progetto" in info["matched_tokens"]
    assert info["overlap"] >= 1


def test_recent_chat_round_trip_and_order(tmp_path):
    mem = Memory(tmp_path / "m.db")
    mem.add_episode("chat", {"role": "user", "text": "ciao"}, category="chat")
    mem.add_episode("chat", {"role": "assistant", "text": "ciao a te"}, category="chat")
    mem.add_episode("chat", {"role": "user", "text": "onb"}, category="onboarding")  # escluso
    history = mem.recent_chat(limit=20)
    assert history == [
        {"role": "user", "content": "ciao"},
        {"role": "assistant", "content": "ciao a te"},
    ]
    mem.close()


def test_recent_chat_limit_keeps_latest(tmp_path):
    mem = Memory(tmp_path / "m2.db")
    for i in range(30):
        mem.add_episode("chat", {"role": "user", "text": f"msg{i}"}, category="chat")
    history = mem.recent_chat(limit=5)
    assert len(history) == 5
    assert history[-1]["content"] == "msg29"     # cronologico, ultimo = piu' recente
    mem.close()


def test_recent_chat_records_preserve_episode_ids_for_provenance(tmp_path):
    mem = Memory(tmp_path / "records.db")
    expected = mem.add_episode(
        "chat", {"role": "user", "text": "dato esplicito"}, category="chat")
    records = mem.recent_chat_records()
    assert records == [{
        "id": expected,
        "ts": records[0]["ts"],
        "role": "user",
        "content": "dato esplicito",
    }]
    mem.close()


def test_history_persists_across_sessions(tmp_path, monkeypatch):
    """M1: una nuova istanza SEED ricarica la conversazione precedente."""
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())
    app.memory.add_episode("chat", {"role": "user", "text": "mi chiamo X"}, category="chat")
    app.memory.add_episode("chat", {"role": "assistant", "text": "piacere"}, category="chat")
    app.shutdown()

    app2 = SeedApp(SeedConfig())
    assert {"role": "user", "content": "mi chiamo X"} in app2._history
    assert {"role": "assistant", "content": "piacere"} in app2._history
    assert len(app2._history) == 2               # niente onboarding, solo chat
    app2.shutdown()
