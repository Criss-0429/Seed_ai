"""Command router deterministico: puro Python prima, LLM solo come normalizzatore.

Filosofia (decisione di Cristian, non negoziabile):
  - il tool calling dei COMANDI e' codice puro: pattern, alias, fuzzy match;
  - l'LLM interviene UNA volta per frase mai vista ("dimmi l'orario" ===
    "che ore sono"?) e il risultato diventa un alias persistente: dalla
    seconda volta in poi il comando costa zero token;
  - gli intent banali (ora, data) hanno handler locali: zero API, zero sandbox.

Pipeline di match (in ordine, si ferma al primo hit):
  1. pattern seed (regex minime per intent, con cattura argomenti)
  2. alias esatto (SQLite, appreso)
  3. fuzzy match sugli alias noti (difflib, soglia alta)
  4. [solo frasi corte] LLM normalizzatore -> se intent valido, salva alias
  5. nessun match -> il messaggio va al flusso conversazionale normale
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

log = logging.getLogger("seed.router")

_FUZZY_THRESHOLD = 0.88
_MAX_WORDS_FOR_LLM = 7  # solo frasi corte/imperative tentano la classificazione
_LOCAL_MEMORY_INTENTS = {"list_preferences"}
# Intent di RECALL: rileggono dati salvati. Devono partire SOLO da un comando
# esplicito (pattern seed), mai essere indovinati dal normalizzatore LLM: una
# domanda come "come sai X su di me?" non deve diventare un dump del database.
# (wiki: recall = metacognitive_depth 2, comando esplicito; "usa la conoscenza
# solo quando rilevante").
_RECALL_INTENTS = frozenset({"list_preferences", "list_notes", "list_knowledge"})
_SEED_PATTERN_ONLY_INTENTS = _RECALL_INTENTS | frozenset({
    "show_living_profile", "show_profile_counterpoint",
    "approve_living_profile", "approve_profile_counterpoint",
})
_EXPLICIT_PREFERENCE_PATTERNS = (
    re.compile(r"^\s*preferisco\s+(?P<value>.+?)\s*[.!?]*$", re.IGNORECASE),
    re.compile(
        r"^\s*(?:ricorda|tieni a mente)\s+che\s+(?P<value>.+?)\s*[.!?]*$",
        re.IGNORECASE,
    ),
)

_NORMALIZER_PROMPT = """Classifica il comando dell'utente in uno di questi intent:
%s
Rispondi SOLO JSON: {"intent": "<id>"} oppure {"intent": "none"} se non e' un comando
diretto ma conversazione. Estrai anche l'argomento se previsto:
{"intent": "open_app", "arg": "spotify"}."""


def normalize(text: str) -> str:
    """lowercase, niente accenti, niente punteggiatura, spazi collassati."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Route:
    intent: str
    args: dict
    source: str       # alias | seed | fuzzy | llm
    local: bool       # True = handler locale, niente sandbox/LLM


@dataclass
class Intent:
    intent_id: str
    description: str          # mostrata al normalizzatore LLM
    seed_patterns: list[str]  # regex; gruppo 'arg' opzionale
    capability_id: str | None = None          # se mappa a una capability
    local_handler: Callable[[dict], str] | None = None  # se e' pure-core
    arg_name: str | None = None


# ---------------------------------------------------------------------------
# handler locali: zero token, zero sandbox
# ---------------------------------------------------------------------------
def _h_time(_args: dict) -> str:
    return datetime.now().strftime("Sono le %H:%M.")


def _h_date(_args: dict) -> str:
    giorni = ["lunedi", "martedi", "mercoledi", "giovedi",
              "venerdi", "sabato", "domenica"]
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
            "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    now = datetime.now()
    return f"Oggi e' {giorni[now.weekday()]} {now.day} {mesi[now.month - 1]} {now.year}."


_BUILTIN_INTENTS: list[Intent] = [
    Intent("tell_time", "dire l'ora corrente",
           [r"\bche ore sono\b", r"\bdimmi l ?orario\b", r"\bche ora e\b",
            r"^orario$", r"^ora$", r"\bwhat time\b"],
           local_handler=_h_time),
    Intent("tell_date", "dire la data di oggi",
           [r"\bche giorno e\b", r"\bdimmi la data\b", r"^data$",
            r"\bquanti ne abbiamo\b", r"\bwhat day\b"],
           local_handler=_h_date),
    Intent("open_app", "aprire un'applicazione (arg = nome app)",
           [r"\b(?:apri|avvia|lancia|open|start)\s+(?P<arg>[\w .-]{2,40})$"],
           capability_id="open_app", arg_name="app"),
    Intent("daily_digest", "riepilogo della giornata osservata",
           [r"\briepilogo\b", r"\bcom e andata oggi\b", r"\bdigest\b",
            r"\bcosa ho fatto oggi\b"],
           capability_id="daily_digest"),
    Intent("take_note", "salvare una nota (arg = testo della nota)",
           [r"\b(?:prendi nota|annota|nota che|salva nota)[: ]+(?P<arg>.+)$"],
           capability_id="take_note", arg_name="text"),
    Intent("list_notes", "rileggere le note salvate",
           [r"\b(?:le mie note|leggi le note|mostrami le note|note salvate)\b"],
           capability_id="take_note"),
    Intent("list_preferences", "rileggere le preferenze esplicite dell'utente",
           [r"\b(?:ricordami cosa preferisco|cosa preferisco|quali sono le mie preferenze|"
            r"mostrami le mie preferenze)\b"]),
]


class CommandRouter:
    def __init__(self, memory, llm=None, runtime_model: str | None = None):
        self._memory = memory
        self._llm = llm                      # opzionale: senza LLM, step 4 saltato
        self._runtime_model = runtime_model
        self._intents: dict[str, Intent] = {i.intent_id: i for i in _BUILTIN_INTENTS}
        # Self-heal: rimuove alias di recall appresi male da sessioni precedenti
        # (una domanda mappata per errore su list_preferences/list_notes).
        pruned = self._memory.prune_aliases_for_intents(_RECALL_INTENTS)
        if pruned:
            log.info("rimossi %d alias di recall appresi male", pruned)

    def register_intent(self, intent: Intent) -> None:
        """Usato dal forge: una capability generata puo' dichiarare seed pattern."""
        self._intents[intent.intent_id] = intent

    def capture_explicit_preference(self, text: str) -> str | None:
        """Persist only clearly explicit, already-redacted preference statements."""
        for pattern in _EXPLICIT_PREFERENCE_PATTERNS:
            match = pattern.match(text)
            if not match:
                continue
            value = match.group("value").strip().rstrip(".!?").strip()
            if not value:
                return None
            digest = hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()[:16]
            key = f"explicit:{digest}"
            self._memory.set_preference(key, value, explicit=True)
            self._memory.add_event("explicit_preference_recorded", {"key": key})
            return value
        return None

    # ------------------------------------------------------------------
    def try_route(self, text: str) -> Route | None:
        norm = normalize(text)
        if not norm:
            return None

        # 1. pattern seed: autorita' core, vince su eventuali alias appresi male
        for intent in self._intents.values():
            for pat in intent.seed_patterns:
                m = re.search(pat, norm)
                if m:
                    args = {}
                    if intent.arg_name and m.groupdict().get("arg"):
                        args[intent.arg_name] = m.group("arg").strip()
                    return Route(intent.intent_id, args, "seed",
                                 self._is_local(intent))

        # 2. alias esatto (appreso)
        hit = self._memory.alias_lookup(norm)
        if hit:
            intent = self._intents.get(hit["intent"])
            if intent:
                return Route(intent.intent_id, hit.get("args", {}),
                             "alias", self._is_local(intent))

        # 3. fuzzy sugli alias noti (puro Python)
        known = self._memory.alias_all()
        if known:
            best = difflib.get_close_matches(norm, list(known), n=1,
                                             cutoff=_FUZZY_THRESHOLD)
            if best:
                hit = known[best[0]]
                intent = self._intents.get(hit["intent"])
                if intent:
                    return Route(intent.intent_id, hit.get("args", {}),
                                 "fuzzy", self._is_local(intent))

        # 4. LLM normalizzatore — SOLO frasi corte, UNA volta, poi alias gratis
        if self._llm is not None and len(norm.split()) <= _MAX_WORDS_FOR_LLM:
            route = self._llm_normalize(norm)
            if route:
                return route
        return None

    # ------------------------------------------------------------------
    def execute(self, route: Route, registry) -> str:
        """Esegue la route. Locale = zero costi; capability = sandbox gated."""
        intent = self._intents[route.intent]
        if route.intent == "list_preferences":
            values = list(self._memory.preferences().values())
            if not values:
                return "Non ho ancora preferenze esplicite salvate."
            return "Preferenze esplicite:\n" + "\n".join(
                f"- {value}" for value in values[-10:]
            )
        if intent.local_handler is not None:
            return intent.local_handler(route.args)
        args = dict(route.args)
        if route.intent == "list_notes":
            args["action"] = "list"
        elif route.intent == "take_note":
            args["action"] = "save"
        result = registry.invoke(intent.capability_id, args)
        return _humanize(route.intent, result)

    # ------------------------------------------------------------------
    def _llm_normalize(self, norm: str) -> Route | None:
        catalog = "\n".join(f"- {i.intent_id}: {i.description}"
                            for i in self._intents.values())
        try:
            resp = self._llm.chat(
                [{"role": "system", "content": _NORMALIZER_PROMPT % catalog},
                 {"role": "user", "content": norm}],
                model=self._runtime_model, redacted=True,
                temperature=0.0, response_json=True)
            from .llm import parse_json_object
            data = parse_json_object(resp.text)
        except Exception as exc:
            log.debug("normalizzatore non disponibile: %s", exc)
            return None
        intent_id = data.get("intent", "none")
        if intent_id in _SEED_PATTERN_ONLY_INTENTS:
            # Recall e approvazioni richiedono un comando core esplicito:
            # niente route indovinata, niente alias appreso.
            log.debug("normalizzatore ha proposto intent esplicito '%s': ignorato",
                      intent_id)
            return None
        intent = self._intents.get(intent_id)
        if intent is None:
            return None
        args = {}
        if intent.arg_name and data.get("arg"):
            args[intent.arg_name] = str(data["arg"]).strip()
        # APPRENDIMENTO: la prossima volta questo comando costa zero
        self._memory.alias_store(norm, intent_id, args)
        self._memory.add_event("alias_learned", {"intent": intent_id})
        return Route(intent_id, args, "llm", self._is_local(intent))

    @staticmethod
    def _is_local(intent: Intent) -> bool:
        return intent.local_handler is not None or intent.intent_id in _LOCAL_MEMORY_INTENTS


# ---------------------------------------------------------------------------
def _humanize(intent: str, result: dict) -> str:
    """Risposta testuale senza LLM per gli esiti delle capability."""
    if result.get("denied"):
        return "Va bene, non lo faccio."
    if "error" in result:
        return f"Non ci sono riuscito: {result['error']}"
    if intent == "open_app":
        return f"Apro {result.get('app', 'l applicazione')}."
    if intent == "daily_digest":
        return result.get("digest", "Fatto.")
    if intent == "take_note":
        return "Annotato."
    if intent == "list_notes":
        notes = result.get("notes", [])
        if not notes:
            return "Nessuna nota salvata."
        return "Le tue note:\n" + "\n".join(
            f"- {n.get('text', '')}" for n in notes[-10:])
    return "Fatto."
