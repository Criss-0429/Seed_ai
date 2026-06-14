"""Test del command router deterministico (v0.2).

Verifica la regola di Cristian: tool calling in puro Python dove possibile,
LLM solo come normalizzatore una-tantum che produce alias persistenti.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.memory import Memory  # noqa: E402
from seed.core.router import CommandRouter, normalize  # noqa: E402


class MockLLM:
    """Conta le chiamate: la regola e' che dalla seconda volta non venga toccato."""

    def __init__(self, intent="tell_time", arg=None):
        self.calls = 0
        self.intent = intent
        self.arg = arg

    def chat(self, messages, **kw):
        from seed.core.llm import LLMResponse
        self.calls += 1
        body = {"intent": self.intent}
        if self.arg:
            body["arg"] = self.arg
        return LLMResponse(text=json.dumps(body))


@pytest.fixture()
def setup(tmp_path):
    mem = Memory(tmp_path / "r.db")
    llm = MockLLM()
    return CommandRouter(mem, llm=llm), mem, llm


class TestNormalize:
    def test_accents_punct_case(self):
        assert normalize("  Ché ORE sono?! ") == "che ore sono"

    def test_collapse_spaces(self):
        assert normalize("apri   spotify") == "apri spotify"


class TestSeedPatterns:
    def test_time_zero_llm(self, setup):
        router, _, llm = setup
        route = router.try_route("Che ore sono?")
        assert route and route.intent == "tell_time" and route.source == "seed"
        assert route.local is True          # handler locale: zero sandbox
        assert llm.calls == 0               # zero token
        out = router.execute(route, registry=None)
        assert "Sono le" in out

    def test_date_local(self, setup):
        router, _, llm = setup
        route = router.try_route("che giorno è oggi")
        assert route and route.intent == "tell_date" and llm.calls == 0
        assert "Oggi e'" in router.execute(route, registry=None)

    def test_open_app_arg_extraction(self, setup):
        router, _, llm = setup
        route = router.try_route("apri spotify")
        assert route and route.intent == "open_app"
        assert route.args == {"app": "spotify"} and llm.calls == 0

    def test_take_note_arg(self, setup):
        router, _, _ = setup
        route = router.try_route("prendi nota: comprare il latte")
        assert route and route.intent == "take_note"
        assert route.args["text"] == "comprare il latte"

    def test_explicit_preference_capture_and_local_recall(self, setup):
        router, mem, llm = setup
        assert router.capture_explicit_preference(
            "Preferisco risposte brevi e dirette."
        ) == "risposte brevi e dirette"
        route = router.try_route("Ricordami cosa preferisco.")
        assert route and route.intent == "list_preferences" and route.local
        assert "risposte brevi e dirette" in router.execute(route, registry=None)
        assert list(mem.preferences().values()) == ["risposte brevi e dirette"]
        assert llm.calls == 0

    def test_seed_pattern_overrides_stale_learned_alias(self, setup):
        router, mem, _ = setup
        mem.alias_store("ricordami cosa preferisco", "list_notes", {})
        route = router.try_route("Ricordami cosa preferisco")
        assert route and route.intent == "list_preferences" and route.source == "seed"

    def test_conversation_not_routed(self, setup):
        """Frasi conversazionali lunghe non devono nemmeno tentare l'LLM."""
        router, _, llm = setup
        long_msg = ("oggi mi sento un po' strano e volevo parlarti di come "
                    "sta andando il progetto che sto seguendo a lavoro")
        assert router.try_route(long_msg) is None
        assert llm.calls == 0


class TestAliasLearning:
    def test_llm_once_then_free(self, setup):
        """'dimmi che ora fa' (mai vista) -> 1 chiamata LLM -> alias -> 0 chiamate."""
        router, mem, llm = setup
        phrase = "dimmi che ora fa adesso"
        r1 = router.try_route(phrase)
        assert r1 and r1.intent == "tell_time" and r1.source == "llm"
        assert llm.calls == 1
        r2 = router.try_route(phrase)
        assert r2 and r2.source == "alias"
        assert llm.calls == 1               # NESSUNA nuova chiamata
        assert normalize(phrase) in mem.alias_all()

    def test_fuzzy_match_on_known_alias(self, setup):
        router, mem, llm = setup
        mem.alias_store("dammi l orario per favore", "tell_time", {})
        route = router.try_route("dammi l orario per favoree")  # typo
        assert route and route.intent == "tell_time" and route.source == "fuzzy"
        assert llm.calls == 0

    def test_llm_none_not_cached(self, setup):
        router, mem, llm = setup
        llm.intent = "none"
        assert router.try_route("frase ambigua breve") is None
        assert llm.calls == 1
        assert mem.alias_all() == {}        # 'none' non diventa alias

    def test_llm_fenced_json_is_accepted(self, setup):
        router, _, llm = setup

        def fenced_chat(messages, **kw):
            from seed.core.llm import LLMResponse
            llm.calls += 1
            return LLMResponse(text='```json\n{"intent":"tell_time"}\n```')

        llm.chat = fenced_chat
        route = router.try_route("dimmi che ora fa adesso")
        assert route and route.intent == "tell_time"

    def test_router_without_llm_still_works(self, tmp_path):
        """Senza LLM configurato il router funziona con seed+alias+fuzzy."""
        mem = Memory(tmp_path / "n.db")
        router = CommandRouter(mem, llm=None)
        assert router.try_route("che ore sono").intent == "tell_time"
        assert router.try_route("frase mai vista xyz") is None


class TestRecallDiscipline:
    """Il recall (rilettura dati salvati) parte SOLO da comando esplicito,
    mai indovinato dal normalizzatore LLM: una domanda non diventa un dump."""

    def test_llm_cannot_route_question_to_preferences_dump(self, setup):
        router, mem, llm = setup
        llm.intent = "list_preferences"          # il modello lo propone per errore
        # "come sai che io corrisponda agli accelerazionisti" (7 parole, tenta LLM)
        assert router.try_route("come sai che io corrisponda agli accelerazionisti") is None
        assert mem.alias_all() == {}             # nessun alias di recall appreso
        assert llm.calls == 1

    def test_llm_cannot_route_question_to_notes_dump(self, setup):
        router, mem, llm = setup
        llm.intent = "list_notes"
        assert router.try_route("ti ricordi cosa ti ho raccontato prima") is None
        assert mem.alias_all() == {}

    def test_explicit_preference_recall_still_works(self, setup):
        router, mem, llm = setup
        router.capture_explicit_preference("Preferisco risposte brevi.")
        route = router.try_route("cosa preferisco")     # comando esplicito (seed)
        assert route and route.intent == "list_preferences" and route.source == "seed"
        assert llm.calls == 0

    def test_startup_prunes_stale_recall_aliases(self, tmp_path):
        mem = Memory(tmp_path / "p.db")
        mem.alias_store("come sai che io sia accelerazionista", "list_preferences", {})
        mem.alias_store("dammi l orario", "tell_time", {})      # azione: resta
        CommandRouter(mem, llm=None)                            # init = self-heal
        aliases = mem.alias_all()
        assert "come sai che io sia accelerazionista" not in aliases
        assert "dammi l orario" in aliases                     # non-recall preservato


class TestHumanize:
    def test_denied(self, setup):
        from seed.core.router import _humanize
        assert "non lo faccio" in _humanize("open_app", {"denied": True, "error": "x"})

    def test_notes_list(self, setup):
        from seed.core.router import _humanize
        out = _humanize("list_notes", {"ok": True, "notes": [{"text": "latte"}]})
        assert "latte" in out
