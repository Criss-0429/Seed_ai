"""Tests for S7 conversational onboarding core."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.memory import Memory  # noqa: E402
from seed.core.onboarding import OnboardingEngine, OnboardingError  # noqa: E402


class MockLLM:
    configured = True

    def __init__(self, responses: list[dict] | None = None):
        self.responses = list(responses or [])
        self.calls = 0
        self.inputs: list[str] = []

    def chat(self, messages, **kwargs):
        del kwargs
        self.calls += 1
        self.inputs.append(messages[-1]["content"])
        payload = self.responses.pop(0) if self.responses else {"hypotheses": []}
        return LLMResponse(text=json.dumps(payload))


def _engine(tmp_path, llm=None) -> tuple[OnboardingEngine, Memory]:
    memory = Memory(tmp_path / "onboarding.db")
    return OnboardingEngine(memory, llm), memory


def _to_summary(engine: OnboardingEngine) -> None:
    assert engine.handle("accetto").text
    assert engine.handle(
        "Lavoro su progetti creativi e vorrei un assistente affidabile.", episode_id=1
    ).text
    assert engine.handle(
        "Mi aiuta chi segnala presto i problemi senza perdere tempo.", episode_id=2
    ).text
    for choice in ("1", "2", "1", "2"):
        assert engine.handle(choice).text
    assert engine.state["phase"] == "summary"


def test_new_user_sees_consent_before_personal_questions(tmp_path):
    engine, memory = _engine(tmp_path)

    assert engine.state["phase"] == "consent"
    assert "Scrivi 'accetto'" in engine.opening_prompt()
    reply = engine.handle("Mi chiamo Luca e faccio il designer")

    assert "scelta esplicita" in reply.text
    assert engine.state["phase"] == "consent"
    assert memory.onboarding_items() == []


def test_decline_pauses_and_resume_returns_to_consent(tmp_path):
    engine, memory = _engine(tmp_path)

    reply = engine.handle("rifiuto")

    assert "Non raccolgo altro" in reply.text
    assert engine.state["phase"] == "paused"
    assert engine.state["consent"]["local_memory"] is False
    assert engine.handle("messaggio personale che non va raccolto").text.startswith(
        "Onboarding in pausa"
    )
    assert memory.onboarding_items() == []
    assert "accetto" in engine.handle("riprendi onboarding").text
    assert engine.state["phase"] == "consent"


def test_explicit_revocation_pauses_future_collection(tmp_path, monkeypatch):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())
    app.handle_message("accetto")
    episodes_before = len(app.memory.episodes_since(0))

    reply = app.handle_message("revoca consenso")
    app.handle_message("email dopo revoca: stop@example.com")

    assert "Consenso revocato" in reply
    assert app.onboarding.state["phase"] == "paused"
    assert len(app.memory.episodes_since(0)) == episodes_before + 1
    assert app.memory.pii_map_all() == []
    app.memory.close()


def test_skip_is_blocked_before_consent_but_allowed_after(tmp_path):
    engine, _ = _engine(tmp_path)

    blocked = engine.handle("salta onboarding")
    assert "prima serve consenso" in blocked.text
    assert engine.state["phase"] == "consent"

    engine.handle("accetto")
    skipped = engine.handle("salta onboarding")
    assert skipped.completed is True
    assert engine.state["completion_mode"] == "skipped"


def test_short_narrative_does_not_advance(tmp_path):
    engine, _ = _engine(tmp_path)
    engine.handle("accetto")

    reply = engine.handle("non so")

    assert "qualcosa in piu" in reply.text
    assert engine.state["phase"] == "story"


def test_hypotheses_are_low_confidence_and_diagnostic_labels_are_rejected(tmp_path):
    llm = MockLLM(
        [
            {
                "hypotheses": [
                    {
                        "statement": "Potrebbe preferire aggiornamenti anticipati sui rischi",
                        "confidence": 0.91,
                    },
                    {
                        "statement": "Ha una personalita introversa e ansiosa",
                        "confidence": 0.2,
                    },
                    {"statement": "Preferisce chiarezza operativa", "confidence": "nan"},
                ]
            }
        ]
    )
    engine, memory = _engine(tmp_path, llm)
    engine.handle("accetto")

    reply = engine.handle(
        "Lavoro meglio quando i problemi vengono segnalati presto.", episode_id=9
    )
    hypotheses = memory.onboarding_items("hypothesis")

    assert reply.llm_used is True
    assert llm.calls == 1
    assert len(hypotheses) == 1
    assert hypotheses[0]["confidence"] == 0.45
    assert hypotheses[0]["explicit"] is False
    assert hypotheses[0]["provenance"] == [9]
    assert "personalita" not in hypotheses[0]["statement"].lower()


def test_pairwise_choices_persist_explicit_preferences_and_invalid_does_not_advance(
    tmp_path,
):
    engine, memory = _engine(tmp_path)
    engine.handle("accetto")
    engine.handle("Mi occupo di design e sviluppo prodotti digitali.", episode_id=1)
    engine.handle("Non mi piace quando un problema viene nascosto.", episode_id=2)

    invalid = engine.handle("dipende")
    assert "Scelta non chiara" in invalid.text
    assert engine.state["pairwise_index"] == 0

    for choice in ("breve", "spontaneamente", "contraddicimi", "spiegami prima"):
        engine.handle(choice)

    preferences = memory.preferences()
    assert engine.state["phase"] == "summary"
    assert preferences == {
        "onboarding:response_form": "risposte brevi e dirette",
        "onboarding:proactivity": "suggerimenti spontanei quando utili",
        "onboarding:challenge": "dissenso diretto quando serve",
        "onboarding:correction": "spiegare il dubbio prima della correzione",
    }
    assert all(item["explicit"] for item in memory.onboarding_items("preference"))


def test_summary_accepts_correction_unknown_and_confirmation(tmp_path):
    engine, memory = _engine(tmp_path)
    _to_summary(engine)

    correction = engine.handle("correggi: non suggerire attività durante il focus", episode_id=4)
    unknown = engine.handle("lascia sconosciuto: vita privata", episode_id=5)
    completed = engine.handle("confermo")

    assert "Correzioni esplicite" in correction.text
    assert "Aree lasciate sconosciute" in unknown.text
    assert completed.completed is True
    assert engine.complete is True
    assert memory.onboarding_items("correction")[0]["provenance"] == [4]
    assert memory.onboarding_items("unknown")[0]["statement"] == "vita privata"


def test_reopen_resumes_same_phase_and_items(tmp_path):
    db_path = tmp_path / "persistent.db"
    first_memory = Memory(db_path)
    first = OnboardingEngine(first_memory)
    first.handle("accetto")
    first.handle("Lavoro su software e ricerca applicata ogni giorno.", episode_id=3)
    first_memory.close()

    second_memory = Memory(db_path)
    second = OnboardingEngine(second_memory)

    assert second.state["phase"] == "collaboration"
    assert second.memory.onboarding_items("story_episode_ref")[0]["provenance"] == [3]
    second_memory.close()


def test_reset_works_after_completion_and_removes_onboarding_preferences(tmp_path):
    engine, memory = _engine(tmp_path)
    memory.add_episode("chat", {"role": "user", "text": "redacted"}, category="onboarding")
    _to_summary(engine)
    engine.handle("confermo")

    reply = engine.handle("ricomincia onboarding")

    assert "accetto" in reply.text
    assert engine.state["phase"] == "consent"
    assert memory.preferences() == {}
    assert memory.onboarding_items() == []
    assert memory.episodes_since(0) == []


def test_corrupt_persisted_state_is_rejected(tmp_path):
    memory = Memory(tmp_path / "bad.db")
    memory.set_onboarding_state(
        {
            "schema_version": "seed.onboarding.v1",
            "phase": "diagnosis",
            "pairwise_index": 0,
            "consent": {},
        }
    )

    with pytest.raises(OnboardingError, match="invalid onboarding phase"):
        OnboardingEngine(memory)


def test_seed_app_redacts_onboarding_story_and_then_releases_normal_chat(
    tmp_path, monkeypatch
):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())
    original_persona = app.evolution.ui_manifest()["persona"].copy()

    app.handle_message("Sono Luca, email luca.preconsenso@example.com")
    assert app.memory.episodes_since(0) == []
    assert app.memory.pii_map_all() == []
    assert app.watcher.paused is True

    assert "Parlami" in app.handle_message("accetto")
    app.handle_message(
        "Sono Luca, scrivimi a luca.personale@example.com e lavoro nel design."
    )
    episodes = app.memory.episodes_since(0)
    serialized = json.dumps(episodes, ensure_ascii=False)
    assert "luca.personale@example.com" not in serialized
    assert "[EMAIL]" in serialized
    assert app.memory.pii_map_all() == []

    app.handle_message("Collaboro bene con chi espone subito i rischi.")
    for choice in ("1", "2", "1", "2"):
        app.handle_message(choice)
    final = app.handle_message("confermo")
    normal = app.handle_message("che ore sono")

    assert "Possiamo iniziare" in final
    assert "Sono le" in normal
    assert app.watcher.paused is False
    assert app.evolution.ui_manifest()["persona"] == original_persona
    assert app.evolution.lineage.events() == []
    app.memory.close()


def test_onboarding_episodes_are_excluded_from_reflection_diary(tmp_path, monkeypatch):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    app = SeedApp(SeedConfig())

    app.handle_message("accetto")
    app.handle_message("Collaboro bene con chi espone subito i rischi.")
    diary = app.evolution._collect_diary()

    assert "Collaboro bene" not in diary
    app.memory.close()
