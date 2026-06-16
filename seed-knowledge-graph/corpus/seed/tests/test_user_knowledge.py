"""Test K1 semantica user-knowledge: cattura esplicita deterministica,
sensibilita', correzione via supersession, recall esplicito."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden, user_knowledge  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.knowledge import KnowledgeStore  # noqa: E402
from seed.core.memory import Memory  # noqa: E402


# -- cattura deterministica -------------------------------------------------

def test_captures_name():
    claims = user_knowledge.capture_explicit("Mi chiamo Cristian")
    assert len(claims) == 1
    assert claims[0].claim_type == "fact" and claims[0].subject == "nome"
    assert claims[0].value == "Cristian" and claims[0].confidence_source == "explicit"


def test_captures_residence_and_job():
    assert user_knowledge.capture_explicit("vivo a Milano")[0].subject == "residenza"
    job = user_knowledge.capture_explicit("lavoro come sviluppatore")[0]
    assert job.subject == "lavoro" and job.value == "sviluppatore"


def test_splits_compound_explicit_statement_with_provenance():
    claims = user_knowledge.capture_explicit(
        "vivo a Roma e sono interessato al mondo dei videogame",
        provenance=[42],
    )
    assert [(c.subject, c.value) for c in claims] == [
        ("residenza", "Roma"),
        ("interesse", "mondo dei videogame"),
    ]
    assert all(c.provenance == [42] for c in claims)


def test_repairs_existing_compound_residence_claim():
    rows = [{
        "claim_type": "relation",
        "subject": "residenza",
        "value": "Roma e sono interessato al mondo dei videogame",
        "provenance": [9],
    }]
    claims = user_knowledge.repair_compound_claims(rows)
    assert [(c.subject, c.value) for c in claims] == [
        ("residenza", "Roma"),
        ("interesse", "mondo dei videogame"),
    ]
    assert all(c.provenance == [9] for c in claims)


def test_captures_boundary():
    c = user_knowledge.capture_explicit("non voglio che mi mandi notifiche")[0]
    assert c.claim_type == "boundary" and c.subject == "confine"


def test_plain_conversation_captures_nothing():
    assert user_knowledge.capture_explicit("oggi che tempo fa?") == []
    assert user_knowledge.capture_explicit("secondo te e' una buona idea?") == []


def test_sensitivity_flagged():
    c = user_knowledge.capture_explicit("non usare i miei dati di salute")[0]
    assert c.sensitivity == "sensitive"


# -- correzione via supersession --------------------------------------------

def test_restatement_supersedes_old_value(tmp_path):
    mem = Memory(tmp_path / "uk.db")
    store = KnowledgeStore(mem)
    for c in user_knowledge.capture_explicit("vivo a Milano"):
        store.record(c)
    for c in user_knowledge.capture_explicit("vivo a Roma"):   # correzione
        store.record(c)
    active = mem.active_knowledge(claim_type="relation")
    assert len(active) == 1 and active[0]["value"] == "Roma"
    mem.close()


# -- recall esplicito a livello app -----------------------------------------

def test_knowledge_recall_excludes_sensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    app = SeedApp(SeedConfig())
    for c in user_knowledge.capture_explicit("vivo a Torino"):
        app.knowledge_store.record(c)
    for c in user_knowledge.capture_explicit("non usare i miei dati di salute"):
        app.knowledge_store.record(c)
    out = app._knowledge_recall()
    assert "Torino" in out
    assert "salute" not in out                 # claim sensibile escluso
    app.shutdown()


def test_knowledge_recall_intent_is_explicit_command(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    app = SeedApp(SeedConfig())
    route = app.router.try_route("cosa sai di me")
    assert route is not None and route.intent == "list_knowledge"
    assert route.source == "seed"              # comando esplicito, non LLM
    app.shutdown()


def test_live_capture_records_user_episode_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    app = SeedApp(SeedConfig())
    state = app.onboarding.state
    state["phase"] = "complete"
    state["completion_mode"] = "skipped"
    state["completed_at"] = 1.0
    state["consent"] = {"local_memory": True, "remote_provider_redacted": True}
    app.memory.set_onboarding_state(state)

    app.handle_message("vivo a Roma e sono interessato al mondo dei videogame")
    claims = app.memory.active_knowledge()
    user_records = [
        r for r in app.memory.recent_chat_records()
        if r["role"] == "user"
    ]

    assert len(claims) == 2
    assert user_records
    assert all(c["provenance"] == [user_records[-1]["id"]] for c in claims)
    app.shutdown()
