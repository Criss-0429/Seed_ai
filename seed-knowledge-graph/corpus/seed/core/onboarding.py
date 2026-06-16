"""Persistent, conversational, non-diagnostic onboarding for SEED."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

from .llm import parse_json_object
from .router import normalize


_SCHEMA_VERSION = "seed.onboarding.v1"
_PHASES = {
    "consent",
    "story",
    "collaboration",
    "comparison",
    "summary",
    "paused",
    "complete",
}
_ACCEPT = {"accetto", "si", "va bene", "continua", "iniziamo", "procedi"}
_DECLINE = {"non accetto", "rifiuto", "no", "fermati", "pausa"}
_BLOCKED_HYPOTHESIS_TERMS = {
    "adhd",
    "ansia",
    "archetipo",
    "autismo",
    "big five",
    "depression",
    "diagnos",
    "disturbo",
    "enneagram",
    "introvers",
    "mbti",
    "narcis",
    "personalita",
    "psicologic",
}
_HYPOTHESIS_PROMPT = """Estrai al massimo 3 ipotesi pratiche e correggibili su
come collaborare con l'utente. Il testo e gia redatto.
Non produrre fatti, diagnosi, tratti psicologici, identita, emozioni stabili o
giudizi. Non imitare lo stile. Ogni confidence deve essere <= 0.45.
Rispondi SOLO JSON:
{"hypotheses":[{"statement":"potrebbe preferire ...","confidence":0.35}]}"""


@dataclass(frozen=True)
class OnboardingReply:
    text: str
    consumed: bool = True
    completed: bool = False
    llm_used: bool = False


@dataclass(frozen=True)
class PairwiseChoice:
    key: str
    prompt: str
    first: str
    second: str
    first_aliases: tuple[str, ...]
    second_aliases: tuple[str, ...]


_PAIRWISE = (
    PairwiseChoice(
        "response_form",
        "Come preferisci una risposta normale?\n1. Breve e diretta\n2. Ragionata, con contesto",
        "risposte brevi e dirette",
        "risposte ragionate con contesto",
        ("1", "breve", "diretta", "brevi"),
        ("2", "ragionata", "contesto", "dettagliata"),
    ),
    PairwiseChoice(
        "proactivity",
        "Quando noto qualcosa di utile?\n1. Suggeriscilo solo se lo chiedo\n2. Suggeriscilo spontaneamente",
        "suggerimenti solo su richiesta",
        "suggerimenti spontanei quando utili",
        ("1", "solo se lo chiedo", "su richiesta"),
        ("2", "spontaneamente", "proattivo", "proattiva"),
    ),
    PairwiseChoice(
        "challenge",
        "Quando non sono d'accordo?\n1. Ti contraddico direttamente\n2. Chiedo prima se vuoi un controargomento",
        "dissenso diretto quando serve",
        "chiedere prima di offrire un controargomento",
        ("1", "direttamente", "contraddicimi"),
        ("2", "chiedimi prima", "controargomento"),
    ),
    PairwiseChoice(
        "correction",
        "Quando sbagli?\n1. Ti correggo subito e chiaramente\n2. Spiego prima il dubbio",
        "correzioni immediate e chiare",
        "spiegare il dubbio prima della correzione",
        ("1", "subito", "chiaramente"),
        ("2", "prima il dubbio", "spiegami prima"),
    ),
)


class OnboardingEngine:
    """State machine that collects explicit choices without building persona."""

    def __init__(self, memory, llm=None):
        self.memory = memory
        self.llm = llm
        state = self.memory.onboarding_state()
        if state is None:
            self._save(self._initial_state())
        else:
            self._validate_state(state)

    @property
    def state(self) -> dict[str, Any]:
        state = self.memory.onboarding_state()
        if state is None:
            state = self._initial_state()
            self._save(state)
        self._validate_state(state)
        return state

    @property
    def complete(self) -> bool:
        return self.state["phase"] == "complete"

    def opening_prompt(self) -> str:
        state = self.state
        phase = state["phase"]
        if phase == "consent":
            return (
                "Prima di conoscerci: memoria e profilo restano locali. "
                "Le chat verso il provider vengono redatte. Le mutazioni sono "
                "solo proposte governate e recuperabili; export solo manuale. "
                "Puoi fermarti, correggere o cancellare l'onboarding. "
                "Scrivi 'accetto' per iniziare oppure 'rifiuto'."
            )
        if phase == "story":
            return (
                "Parlami un po' di te, delle tue giornate e di cosa vorresti "
                "da un assistente. Non cerco etichette o diagnosi."
            )
        if phase == "collaboration":
            return (
                "Raccontami un esempio di collaborazione riuscita oppure "
                "frustrante. Mi interessa capire come esserti utile."
            )
        if phase == "comparison":
            return _PAIRWISE[state["pairwise_index"]].prompt
        if phase == "summary":
            return self._summary()
        if phase == "paused":
            return "Onboarding in pausa. Scrivi 'riprendi onboarding' quando vuoi."
        return "Onboarding concluso."

    def handle(self, text: str, *, episode_id: int | None = None) -> OnboardingReply:
        raw = text.strip()
        norm = normalize(raw)
        state = self.state

        control = self._control(norm, state)
        if control is not None:
            return control
        if state["phase"] == "complete":
            return OnboardingReply("", consumed=False, completed=True)

        phase = state["phase"]
        if phase == "paused":
            return OnboardingReply(self.opening_prompt())
        if phase == "consent":
            return self._handle_consent(norm, state)
        if phase == "story":
            return self._handle_narrative(raw, state, "story", episode_id)
        if phase == "collaboration":
            return self._handle_narrative(raw, state, "collaboration", episode_id)
        if phase == "comparison":
            return self._handle_comparison(norm, state)
        if phase == "summary":
            return self._handle_summary(raw, norm, state, episode_id)
        raise OnboardingError(f"unsupported onboarding phase: {phase}")

    def _control(self, norm: str, state: dict[str, Any]) -> OnboardingReply | None:
        if norm in {"pausa onboarding", "metti in pausa onboarding"}:
            if state["phase"] != "paused":
                state["resume_phase"] = state["phase"]
                state["phase"] = "paused"
                self._save(state)
                self.memory.add_event("onboarding_paused", {})
            return OnboardingReply(self.opening_prompt())
        if norm in {"riprendi onboarding", "continua onboarding"}:
            if state["phase"] == "paused":
                state["phase"] = state.get("resume_phase") or "consent"
                state["resume_phase"] = ""
                self._save(state)
                self.memory.add_event("onboarding_resumed", {})
            return OnboardingReply(self.opening_prompt())
        if norm in {"revoca consenso", "revoca il consenso"}:
            state["consent"] = {
                "local_memory": False,
                "remote_provider_redacted": False,
                "evolution_proposals": False,
                "manual_export_only": True,
                "activity_watcher_during_onboarding": False,
            }
            state["resume_phase"] = "consent"
            state["phase"] = "paused"
            self._save(state)
            self.memory.add_event("onboarding_consent_revoked", {})
            return OnboardingReply(
                "Consenso revocato. Non raccolgo altro. I dati onboarding gia "
                "salvati restano locali; scrivi 'reset onboarding' per eliminarli."
            )
        if norm in {"ricomincia onboarding", "reset onboarding"}:
            self.memory.clear_onboarding()
            self._save(self._initial_state())
            self.memory.add_event("onboarding_reset", {})
            return OnboardingReply(self.opening_prompt())
        if norm in {"salta onboarding", "salta"}:
            if not state.get("consent", {}).get("remote_provider_redacted"):
                return OnboardingReply(
                    "Puoi saltare le domande personali, ma prima serve consenso "
                    "esplicito per memoria locale e provider redatto: scrivi "
                    "'accetto' oppure 'rifiuto'."
                )
            state["phase"] = "complete"
            state["completion_mode"] = "skipped"
            state["completed_at"] = time.time()
            self._save(state)
            self.memory.add_event("onboarding_completed", {"mode": "skipped"})
            return OnboardingReply(
                "Onboarding saltato. Potrai ricominciarlo in seguito.",
                completed=True,
            )
        return None

    def _handle_consent(self, norm: str, state: dict[str, Any]) -> OnboardingReply:
        if norm in _ACCEPT:
            state["consent"] = {
                "local_memory": True,
                "remote_provider_redacted": True,
                "evolution_proposals": True,
                "manual_export_only": True,
                "activity_watcher_during_onboarding": False,
            }
            state["phase"] = "story"
            self._save(state)
            self.memory.add_event("onboarding_consent_recorded", {"accepted": True})
            return OnboardingReply(self.opening_prompt())
        if norm in _DECLINE:
            state["consent"] = {
                "local_memory": False,
                "remote_provider_redacted": False,
                "evolution_proposals": False,
                "manual_export_only": True,
                "activity_watcher_during_onboarding": False,
            }
            state["resume_phase"] = "consent"
            state["phase"] = "paused"
            self._save(state)
            self.memory.add_event("onboarding_consent_recorded", {"accepted": False})
            return OnboardingReply(
                "Va bene. Non raccolgo altro. Onboarding in pausa; puoi chiudere "
                "l'app o scrivere 'riprendi onboarding'."
            )
        return OnboardingReply(
            "Per iniziare serve una scelta esplicita: scrivi 'accetto' oppure 'rifiuto'."
        )

    def _handle_narrative(
        self,
        text: str,
        state: dict[str, Any],
        kind: str,
        episode_id: int | None,
    ) -> OnboardingReply:
        if len(text.split()) < 3:
            return OnboardingReply(
                "Puoi dirmi qualcosa in piu, oppure scrivere 'salta onboarding'."
            )
        provenance = [episode_id] if episode_id is not None else []
        self.memory.add_onboarding_item(
            f"{kind}_episode_ref",
            f"episodio redatto #{episode_id}" if episode_id is not None else "episodio redatto",
            1.0,
            True,
            provenance,
        )
        llm_used = self._extract_hypotheses(text, provenance)
        state["phase"] = "collaboration" if kind == "story" else "comparison"
        self._save(state)
        self.memory.add_event("onboarding_narrative_recorded", {"kind": kind})
        return OnboardingReply(self.opening_prompt(), llm_used=llm_used)

    def _handle_comparison(
        self,
        norm: str,
        state: dict[str, Any],
    ) -> OnboardingReply:
        choice = _PAIRWISE[state["pairwise_index"]]
        selected = self._select_pairwise(norm, choice)
        if selected is None:
            return OnboardingReply(
                f"Scelta non chiara. Rispondi 1 oppure 2.\n{choice.prompt}"
            )
        self.memory.set_preference(f"onboarding:{choice.key}", selected, explicit=True)
        self.memory.add_onboarding_item("preference", selected, 1.0, True, [])
        self.memory.add_event("onboarding_pairwise_recorded", {"key": choice.key})
        state["pairwise_index"] += 1
        if state["pairwise_index"] >= len(_PAIRWISE):
            state["phase"] = "summary"
        self._save(state)
        return OnboardingReply(self.opening_prompt())

    def _handle_summary(
        self,
        raw: str,
        norm: str,
        state: dict[str, Any],
        episode_id: int | None,
    ) -> OnboardingReply:
        if norm in {"confermo", "va bene", "corretto", "si"}:
            state["phase"] = "complete"
            state["completion_mode"] = "confirmed"
            state["completed_at"] = time.time()
            self._save(state)
            self.memory.add_event(
                "onboarding_completed",
                {
                    "mode": "confirmed",
                    "preferences": len(self.memory.onboarding_items("preference")),
                    "hypotheses": len(self.memory.onboarding_items("hypothesis")),
                    "corrections": len(self.memory.onboarding_items("correction")),
                },
            )
            return OnboardingReply(
                "Ricevuto. Questa e una base correggibile, non una definizione "
                "di chi sei. Possiamo iniziare.",
                completed=True,
            )
        correction = self._prefixed_value(raw, "correggi:")
        if correction:
            self.memory.add_onboarding_item(
                "correction",
                correction,
                1.0,
                True,
                [episode_id] if episode_id is not None else [],
            )
            self.memory.add_event("onboarding_correction_recorded", {})
            return OnboardingReply(self._summary())
        unknown = self._prefixed_value(raw, "lascia sconosciuto:")
        if unknown:
            self.memory.add_onboarding_item(
                "unknown",
                unknown,
                1.0,
                True,
                [episode_id] if episode_id is not None else [],
            )
            self.memory.add_event("onboarding_unknown_recorded", {})
            return OnboardingReply(self._summary())
        return OnboardingReply(
            "Scrivi 'confermo', 'correggi: ...' oppure 'lascia sconosciuto: ...'.\n\n"
            + self._summary()
        )

    def _extract_hypotheses(self, text: str, provenance: list[int]) -> bool:
        if self.llm is None or not getattr(self.llm, "configured", True):
            return False
        try:
            response = self.llm.chat(
                [
                    {"role": "system", "content": _HYPOTHESIS_PROMPT},
                    {"role": "user", "content": text},
                ],
                redacted=True,
                temperature=0.0,
                response_json=True,
            )
            raw = parse_json_object(response.text).get("hypotheses", [])
            if not isinstance(raw, list):
                return True
            accepted = 0
            for item in raw[:3]:
                if not isinstance(item, dict):
                    continue
                statement = str(item.get("statement") or "").strip()
                if not self._valid_hypothesis(statement):
                    continue
                confidence = float(item.get("confidence", 0.3))
                if not math.isfinite(confidence):
                    continue
                confidence = min(max(confidence, 0.05), 0.45)
                self.memory.add_onboarding_item(
                    "hypothesis", statement[:240], confidence, False, provenance
                )
                accepted += 1
            self.memory.add_event("onboarding_hypotheses_extracted", {"accepted": accepted})
            return True
        except Exception:
            self.memory.add_event("onboarding_hypothesis_extraction_failed", {})
            return True

    def _summary(self) -> str:
        sections = ["Questo e cio che penso di aver capito finora."]
        sections.append(
            self._section("Preferenze esplicite", self.memory.onboarding_items("preference"))
        )
        sections.append(
            self._section(
                "Ipotesi da verificare, non fatti",
                self.memory.onboarding_items("hypothesis"),
                include_confidence=True,
            )
        )
        sections.append(
            self._section("Correzioni esplicite", self.memory.onboarding_items("correction"))
        )
        sections.append(
            self._section("Aree lasciate sconosciute", self.memory.onboarding_items("unknown"))
        )
        sections.append(
            "Scrivi 'confermo', 'correggi: ...' oppure 'lascia sconosciuto: ...'."
        )
        return "\n\n".join(section for section in sections if section)

    @staticmethod
    def _section(title: str, items: list[dict], include_confidence: bool = False) -> str:
        if not items:
            return ""
        lines = []
        for item in items:
            suffix = f" (confidenza {item['confidence']:.2f})" if include_confidence else ""
            lines.append(f"- {item['statement']}{suffix}")
        return title + ":\n" + "\n".join(lines)

    @staticmethod
    def _select_pairwise(norm: str, choice: PairwiseChoice) -> str | None:
        first = any(norm == alias or alias in norm for alias in choice.first_aliases)
        second = any(norm == alias or alias in norm for alias in choice.second_aliases)
        if first == second:
            return None
        return choice.first if first else choice.second

    @staticmethod
    def _prefixed_value(raw: str, prefix: str) -> str:
        if not raw.lower().startswith(prefix):
            return ""
        return raw[len(prefix):].strip()[:500]

    @staticmethod
    def _valid_hypothesis(statement: str) -> bool:
        lowered = statement.lower()
        return (
            8 <= len(statement) <= 240
            and not any(term in lowered for term in _BLOCKED_HYPOTHESIS_TERMS)
        )

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        now = time.time()
        return {
            "schema_version": _SCHEMA_VERSION,
            "phase": "consent",
            "resume_phase": "",
            "pairwise_index": 0,
            "consent": {},
            "started_at": now,
            "updated_at": now,
            "completed_at": None,
            "completion_mode": "",
        }

    def _save(self, state: dict[str, Any]) -> None:
        self._validate_state(state)
        state["updated_at"] = time.time()
        self.memory.set_onboarding_state(state)

    @staticmethod
    def _validate_state(state: dict[str, Any]) -> None:
        if state.get("schema_version") != _SCHEMA_VERSION:
            raise OnboardingError("unsupported onboarding schema")
        if state.get("phase") not in _PHASES:
            raise OnboardingError("invalid onboarding phase")
        index = state.get("pairwise_index")
        if not isinstance(index, int) or not 0 <= index <= len(_PAIRWISE):
            raise OnboardingError("invalid onboarding pairwise index")
        if not isinstance(state.get("consent"), dict):
            raise OnboardingError("invalid onboarding consent")


class OnboardingError(RuntimeError):
    """Raised when persisted onboarding state violates its contract."""
