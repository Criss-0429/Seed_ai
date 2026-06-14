"""M2 conoscenza tipata dell'utente: ontologia + supersession bi-temporale +
contradiction check + estrazione candidate-only.

Lezione dall'analisi mem0 (doc 14): l'accumulo monotonico ADD-only uccide la
memoria per staleness ("dark mode" poi "light mode" -> restano entrambi). Qui
ogni nuovo claim passa da contradiction check: un valore nuovo per la stessa
chiave (claim_type, subject) **supera** il vecchio (bi-temporale), non accumula.

Sicurezza cognitiva (wiki `Jarvis_User_Knowledge_Ontology`): ipotesi != fatto.
L'LLM PROPONE candidate; l'harness promuove. Un'inferenza non sovrascrive mai un
fatto esplicito; resta candidate a bassa confidenza. Nessuna diagnosi clinica.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .llm import parse_json_object
from .router import normalize

log = logging.getLogger("seed.knowledge")

CLAIM_TYPES = (
    "fact", "state", "routine", "pattern", "preference",
    "relation", "exception", "hypothesis", "boundary",
)
CONFIDENCE_SOURCES = ("explicit", "inferred")
# M3: taxonomy edge cognitivi (wiki harness). Tipati, pesati, temporali.
EDGE_TYPES = (
    "supports", "contradicts", "supersedes", "attenuates", "activates",
    "inhibits", "predicts", "explains", "co_occurs", "depends_on",
)
# Tipi che restano sempre candidate: inferenze non confermate, mai fatti.
_ALWAYS_CANDIDATE = {"hypothesis", "pattern"}
_INFERRED_MAX_CONFIDENCE = 0.45        # cap per le inferenze (coerente con S7)


class KnowledgeError(ValueError):
    pass


@dataclass
class UserClaim:
    claim_type: str
    subject: str                 # slot normalizzato: chiave di supersession
    value: str
    confidence: float = 0.6
    confidence_source: str = "explicit"   # explicit | inferred
    scope: str = "private"
    sensitivity: str = "normal"           # normal | sensitive
    provenance: list[int] = field(default_factory=list)

    def validate(self) -> None:
        if self.claim_type not in CLAIM_TYPES:
            raise KnowledgeError(f"claim_type invalido: {self.claim_type}")
        if self.confidence_source not in CONFIDENCE_SOURCES:
            raise KnowledgeError(f"confidence_source invalido: {self.confidence_source}")
        if not self.subject.strip() or not self.value.strip():
            raise KnowledgeError("subject e value sono obbligatori")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise KnowledgeError("confidence fuori range [0,1]")

    def normalized(self) -> "UserClaim":
        """Inferenze: cap confidenza e source 'inferred'. Ipotesi/pattern non
        possono dichiararsi esplicite."""
        self.validate()
        conf = float(self.confidence)
        source = self.confidence_source
        if self.claim_type in _ALWAYS_CANDIDATE and source == "explicit":
            source = "inferred"
        if source == "inferred":
            conf = min(conf, _INFERRED_MAX_CONFIDENCE)
        return UserClaim(self.claim_type, self.subject.strip(), self.value.strip(),
                         conf, source, self.scope, self.sensitivity,
                         list(self.provenance))


class KnowledgeStore:
    """Promozione e supersession governate sopra la tabella `knowledge`."""

    def __init__(self, memory):
        self._m = memory

    def record(self, claim: UserClaim) -> dict:
        """Registra un claim applicando NOOP / supersession / candidate.

        - explicit -> lifecycle 'active' (tranne hypothesis/pattern = candidate);
        - inferred -> 'candidate' (bassa confidenza);
        - stesso (claim_type, subject) con stesso valore -> NOOP;
        - valore diverso: una fonte ALMENO autorevole quanto l'esistente supera
          il vecchio (bi-temporale); un'inferenza NON supera un fatto esplicito.
        """
        claim = claim.normalized()
        # K4 safety gate: un claim SENSIBILE non diventa mai attivo da solo —
        # resta candidate finche' l'utente non conferma ("sensibile -> chiedi").
        lifecycle = "candidate" if (
            claim.confidence_source == "inferred"
            or claim.claim_type in _ALWAYS_CANDIDATE
            or claim.sensitivity == "sensitive"
        ) else "active"

        existing = self._m.knowledge_active_by_key(claim.claim_type, claim.subject)
        superseded = None
        if existing:
            if normalize(existing["value"]) == normalize(claim.value):
                return {"action": "noop", "id": existing["id"],
                        "lifecycle": existing["lifecycle_state"]}
            # contraddizione: chi e' almeno autorevole quanto l'esistente vince
            existing_explicit = existing["confidence_source"] == "explicit" \
                and existing["lifecycle_state"] == "active"
            new_explicit = lifecycle == "active"
            if new_explicit or not existing_explicit:
                self._m.supersede_knowledge(existing["id"])
                # K4 stale cascade: chiudi gli edge del vecchio (tranne la storia)
                self._m.close_edges_for(existing["id"], exclude_type="supersedes")
                superseded = existing["id"]
            else:
                # inferenza che contraddice un fatto esplicito: resta candidate,
                # non supera nulla
                lifecycle = "candidate"

        new_id = self._m.add_knowledge(
            claim_type=claim.claim_type, subject=claim.subject, value=claim.value,
            confidence=claim.confidence, confidence_source=claim.confidence_source,
            provenance=claim.provenance, lifecycle_state=lifecycle,
            scope=claim.scope, sensitivity=claim.sensitivity)
        if superseded is not None:
            # M3: edge semantico esplicito new -> old (storia interrogabile)
            self._m.add_edge(source_id=new_id, target_id=superseded,
                             edge_type="supersedes", weight=1.0,
                             confidence=claim.confidence)
        self._m.add_event("knowledge_recorded", {
            "claim_type": claim.claim_type, "lifecycle": lifecycle,
            "source": claim.confidence_source, "superseded": superseded is not None})
        return {"action": "superseded" if superseded else "added",
                "id": new_id, "lifecycle": lifecycle, "superseded": superseded}


_EXTRACT_PROMPT = (
    "Estrai dai messaggi i claim sull'UTENTE come JSON. Distingui esplicito da "
    "inferito: 'explicit' solo cio' che l'utente ha dichiarato, 'inferred' per "
    "ipotesi prudenti. NESSUNA diagnosi clinica, nessun tratto psicometrico.\n"
    "Tipi ammessi: fact, state, routine, preference, relation, boundary, "
    "hypothesis. 'subject' = slot breve normalizzato (es. residenza, lavoro, "
    "forma_risposta). Rispondi SOLO JSON:\n"
    '{"claims":[{"claim_type":"...","subject":"...","value":"...",'
    '"confidence_source":"explicit|inferred"}]}'
)


class KnowledgeExtractor:
    """Estrae claim CANDIDATE dal testo (gia' redatto) via LLM. Pura: non scrive.
    Il chiamante decide se passarli a `KnowledgeStore.record` (harness promuove).
    Coerente con 'LLM non scrive fatti direttamente'."""

    def extract(self, text: str, llm, *, provenance: list[int] | None = None
                ) -> list[UserClaim]:
        if llm is None or not getattr(llm, "configured", False) or not text.strip():
            return []
        try:
            resp = llm.chat(
                [{"role": "system", "content": _EXTRACT_PROMPT},
                 {"role": "user", "content": text}],
                redacted=True, temperature=0.0, response_json=True)
            data = parse_json_object(resp.text)
        except Exception as exc:
            log.debug("estrazione knowledge fallita: %s", exc)
            return []
        out: list[UserClaim] = []
        for item in data.get("claims") or []:
            if not isinstance(item, dict):
                continue
            try:
                claim = UserClaim(
                    claim_type=str(item.get("claim_type", "")),
                    subject=str(item.get("subject", "")),
                    value=str(item.get("value", "")),
                    confidence_source=str(item.get("confidence_source", "inferred")),
                    confidence=0.6,
                    provenance=list(provenance or []))
                claim.validate()
            except KnowledgeError:
                continue                      # scarta claim malformati, mai eccezione
            out.append(claim)
        return out
