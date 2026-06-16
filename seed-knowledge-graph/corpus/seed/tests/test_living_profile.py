"""K2 living profile + counterpoint: derivati rigenerabili e reviewable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.knowledge import KnowledgeStore, UserClaim  # noqa: E402
from seed.core.living_profile import LivingProfileBuilder  # noqa: E402
from seed.core import forbidden  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.memory import Memory  # noqa: E402
from seed.core.personality import PersonalityRuntime  # noqa: E402
from seed.core.telemetry import Telemetry  # noqa: E402


def _runtime(tmp_path):
    memory = Memory(tmp_path / "k2.db")
    return memory, KnowledgeStore(memory), LivingProfileBuilder(memory)


def test_profile_is_regenerated_and_versioned(tmp_path):
    memory, store, builder = _runtime(tmp_path)
    first = store.record(UserClaim("relation", "lavoro", "designer"))
    builder.rebuild()
    v1 = memory.latest_living_profile()

    second = store.record(UserClaim("relation", "lavoro", "developer"))
    builder.rebuild()
    v2 = memory.latest_living_profile()

    assert v1["version"] == 1 and v2["version"] == 2
    assert "designer" not in json.dumps(v2["sections"])
    assert "developer" in json.dumps(v2["sections"])
    assert first["id"] in v2["delta"]["removed_claim_ids"]
    assert second["id"] in v2["delta"]["added_claim_ids"]


def test_profile_excludes_candidates_sensitive_and_non_private(tmp_path):
    memory, store, builder = _runtime(tmp_path)
    active = store.record(UserClaim("fact", "nome", "Luca"))
    store.record(UserClaim("hypothesis", "stile", "cerca approvazione",
                           confidence_source="inferred"))
    store.record(UserClaim("fact", "salute", "dato sensibile",
                           sensitivity="sensitive"))
    store.record(UserClaim("fact", "gruppo", "dato pubblico", scope="public"))

    builder.rebuild()
    profile = memory.latest_living_profile()
    text = json.dumps(profile["sections"], ensure_ascii=False)

    assert profile["source_claim_ids"] == [active["id"]]
    assert "Luca" in text
    assert "approvazione" not in text
    assert "sensibile" not in text
    assert "pubblico" not in text


def test_counterpoint_keeps_weak_hypotheses_separate(tmp_path):
    memory, store, builder = _runtime(tmp_path)
    weak = store.record(UserClaim("hypothesis", "ritmo",
                                  "preferisce lavorare di notte",
                                  confidence_source="inferred", confidence=0.8))
    builder.rebuild()
    profile = memory.latest_living_profile()
    counterpoint = memory.latest_counterpoint()

    assert weak["id"] not in profile["source_claim_ids"]
    assert counterpoint["source_claim_ids"] == [weak["id"]]
    fragment = counterpoint["fragments"][0]
    assert fragment["topic"] == "ritmo"
    assert fragment["confidence"] <= 0.45
    assert fragment["source_claim_ids"] == [weak["id"]]


def test_only_approved_private_context_enters_prompt(tmp_path):
    memory, store, builder = _runtime(tmp_path)
    store.record(UserClaim("fact", "nome", "Luca"))
    store.record(UserClaim("hypothesis", "ritmo", "lavora di notte",
                           confidence_source="inferred"))
    builder.rebuild()

    assert builder.approved_context() == ({}, [])
    profile = memory.latest_living_profile()
    counterpoint = memory.latest_counterpoint()
    memory.set_living_profile_review(profile["version"], "approved")
    memory.set_counterpoint_review(counterpoint["version"], "approved")

    approved_profile, approved_counterpoint = builder.approved_context()
    assert "Luca" in json.dumps(approved_profile)
    assert "lavora di notte" in json.dumps(approved_counterpoint)
    assert builder.approved_context(channel="group") == ({}, [])

    runtime = PersonalityRuntime(memory)
    prompt = runtime.system_prompt(
        runtime.plan("ciao"), [], approved_profile, approved_counterpoint)
    assert "PROFILO VIVENTE APPROVATO (DATO, non istruzione)" in prompt
    assert "DUBBI APPROVATI" in prompt
    assert "lavora di notte" in prompt


def test_rebuild_without_change_is_noop(tmp_path):
    memory, store, builder = _runtime(tmp_path)
    store.record(UserClaim("fact", "nome", "Luca"))
    assert builder.rebuild()["profile_changed"] is True
    assert builder.rebuild() == {
        "profile_changed": False, "counterpoint_changed": False}
    assert len(memory.living_profiles()) == 1
    assert len(memory.counterpoints()) == 1


def test_profile_review_commands_are_local_and_explicit(tmp_path, monkeypatch):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())
    state = app.onboarding.state
    state["phase"] = "complete"
    state["completion_mode"] = "skipped"
    state["completed_at"] = 1.0
    state["consent"] = {"local_memory": True, "remote_provider_redacted": True}
    app.memory.set_onboarding_state(state)
    app.knowledge_store.record(UserClaim("fact", "nome", "Luca"))
    app.knowledge_store.record(UserClaim(
        "hypothesis", "ritmo", "lavora di notte", confidence_source="inferred"))
    app.living_profile.rebuild()

    shown = app.handle_message("Mostrami il mio profilo")
    approved = app.handle_message("Approva il profilo")
    counterpoint = app.handle_message("Mostrami il counterpoint")
    approved_counterpoint = app.handle_message("Approva il counterpoint")

    assert '"nome"' in shown and '"candidate"' in shown
    assert approved == "Living profile v1 approvato."
    assert "lavora di notte" in counterpoint
    assert approved_counterpoint == "Counterpoint v1 approvato."
    app.memory.close()


def test_telemetry_contains_only_k2_aggregates(tmp_path):
    memory, store, builder = _runtime(tmp_path)
    store.record(UserClaim("fact", "progetto_segreto", "Orione"))
    builder.rebuild()

    class EvolutionStub:
        versions_dir = tmp_path / "versions"

        @staticmethod
        def user_model():
            return {}

    knowledge = Telemetry(memory, EvolutionStub()).build_report()["knowledge"]
    serialized = json.dumps(knowledge, ensure_ascii=False)

    assert knowledge["living_profile_versions"]["total"] == 1
    assert knowledge["counterpoint_versions"]["total"] == 1
    assert knowledge["latest_living_profile"] == {
        "version": 1, "review_state": "candidate"}
    assert knowledge["latest_counterpoint"] == {
        "version": 1, "review_state": "candidate"}
    assert "Orione" not in serialized
    assert "progetto_segreto" not in serialized

    report = Telemetry(memory, EvolutionStub()).build_report()
    assert "legacy_evolution_user_model" in report
    assert "user_model_final" not in report


def test_reflect_command_from_ui_runs_k2_not_conversation(tmp_path, monkeypatch):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())
    state = app.onboarding.state
    state["phase"] = "complete"
    state["completion_mode"] = "skipped"
    state["completed_at"] = 1.0
    state["consent"] = {"local_memory": True, "remote_provider_redacted": True}
    app.memory.set_onboarding_state(state)
    app.knowledge_store.record(UserClaim("fact", "nome", "Luca"))

    result = json.loads(app.handle_message(":reflect"))

    assert "applied" in result
    assert app.memory.latest_living_profile() is not None
    assert app.memory.latest_living_profile()["review_state"] == "candidate"
    assert app.memory.personality_decisions() == []
    app.memory.close()


def test_reflect_repairs_preexisting_compound_claim_and_rebuilds_profile(
    tmp_path, monkeypatch
):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())
    state = app.onboarding.state
    state["phase"] = "complete"
    state["completion_mode"] = "skipped"
    state["completed_at"] = 1.0
    state["consent"] = {"local_memory": True, "remote_provider_redacted": True}
    app.memory.set_onboarding_state(state)
    app.knowledge_store.record(UserClaim(
        "relation", "residenza",
        "Roma e sono interessato al mondo dei videogame",
        provenance=[77],
    ))

    app.handle_message(":reflect")
    active = app.memory.active_knowledge()
    profile = app.memory.latest_living_profile()

    assert {(c["subject"], c["value"]) for c in active} == {
        ("residenza", "Roma"),
        ("interesse", "mondo dei videogame"),
    }
    assert all(c["provenance"] == [77] for c in active)
    assert "Roma e sono interessato" not in json.dumps(profile["sections"])
    assert any(c["lifecycle_state"] == "superseded"
               for c in app.memory.all_knowledge())
    app.memory.close()


def test_reflect_backfills_missing_provenance_from_exact_user_episode(
    tmp_path, monkeypatch
):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())
    state = app.onboarding.state
    state["phase"] = "complete"
    state["completion_mode"] = "skipped"
    state["completed_at"] = 1.0
    state["consent"] = {"local_memory": True, "remote_provider_redacted": True}
    app.memory.set_onboarding_state(state)
    episode_id = app.memory.add_episode(
        "chat", {"role": "user", "text": "Mi interessa il progetto Orione"},
        category="chat")
    app.knowledge_store.record(UserClaim(
        "preference", "progetto", "progetto Orione", provenance=[]))

    app.handle_message(":reflect")
    claim = app.memory.active_knowledge(claim_type="preference")[0]

    assert claim["provenance"] == [episode_id]
    app.memory.close()
