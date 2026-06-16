"""K1 semantica della conoscenza dell'utente sopra il substrato M2.

M2 da' lo store tipato + supersession. K1 aggiunge la semantica del MODELLO
DELL'UTENTE (wiki `Jarvis_User_Knowledge_Ontology`):

- cattura DETERMINISTICA di dichiarazioni esplicite chiare dalla chat (zero
  token), cosi' SEED impara subito i fatti dichiarati, non solo sleep-time;
- correzione = ri-dichiarazione: lo stesso slot con valore nuovo supera il
  vecchio via `KnowledgeStore` (la correzione dell'utente prevale);
- classificazione di sensibilita': i claim sensibili (salute, religione,
  orientamento, politica) restano memorizzati ma NON entrano nel contesto per
  default e non alimentano proattivita' senza consenso.

Conservativa: solo pattern espliciti e stretti, per non inventare claim. Le
inferenze ricche restano all'estrattore LLM candidate-only (M2, sleep-time).
"""

from __future__ import annotations

import re

from .knowledge import UserClaim

# Indizi di sensibilita': il claim viene marcato 'sensitive'.
_SENSITIVE_HINTS = (
    "salut", "malatt", "medic", "terapia", "diagnosi", "farmac", "depress",
    "ansia", "religion", "fede", "orientament", "sessual", "politic", "partito",
)

# Slot espliciti: (claim_type, subject, regex con gruppo 'v'). Stretti di
# proposito. Il valore puo' contenere placeholder del privacy gate ([PERSON_1]).
_VALUE = r"(?P<v>[\w .'\[\]-]{1,80}?)"
_PATTERNS: tuple[tuple[str, str, re.Pattern], ...] = (
    ("fact", "nome",
     re.compile(rf"\bmi chiamo\s+{_VALUE}\s*[.!?]*$", re.IGNORECASE)),
    ("relation", "residenza",
     re.compile(rf"\b(?:vivo|abito)\s+(?:a|in|nel|nella|negli|alle)\s+{_VALUE}\s*[.!?]*$",
                re.IGNORECASE)),
    ("relation", "lavoro",
     re.compile(rf"\b(?:lavoro come|faccio il|faccio la|di mestiere faccio)\s+{_VALUE}\s*[.!?]*$",
                re.IGNORECASE)),
    ("preference", "interesse",
     re.compile(rf"\b(?:sono interessat[oa]\s+(?:a|al|alla|ai|alle)|"
                rf"mi interessa)\s+{_VALUE}\s*[.!?]*$", re.IGNORECASE)),
    ("boundary", "confine",
     re.compile(rf"\bnon voglio che\s+{_VALUE}\s*[.!?]*$", re.IGNORECASE)),
    ("boundary", "confine",
     re.compile(rf"\bnon usare\s+{_VALUE}\s*[.!?]*$", re.IGNORECASE)),
)

_CLAUSE_SPLIT = re.compile(
    r"\s+e\s+(?=(?:sono|mi|vivo|abito|lavoro|faccio|preferisco|non)\b)",
    re.IGNORECASE,
)


def _sensitivity(text: str) -> str:
    low = text.lower()
    return "sensitive" if any(h in low for h in _SENSITIVE_HINTS) else "normal"


def capture_explicit(text: str, *, provenance: list[int] | None = None
                     ) -> list[UserClaim]:
    """Estrae claim espliciti chiari (gia' redatti). Deterministico, zero token.
    Lo stesso slot ridichiarato con valore nuovo -> supersession a valle."""
    claims: list[UserClaim] = []
    for clause in _CLAUSE_SPLIT.split(text.strip()):
        for claim_type, subject, pattern in _PATTERNS:
            m = pattern.search(clause)
            if not m:
                continue
            value = m.group("v").strip().rstrip(".!?").strip()
            if not value:
                continue
            claims.append(UserClaim(
                claim_type=claim_type, subject=subject, value=value,
                confidence=0.9, confidence_source="explicit",
                sensitivity=_sensitivity(subject + " " + value),
                provenance=list(provenance or [])))
    return claims


def repair_compound_claims(rows: list[dict]) -> list[UserClaim]:
    """Ripara solo claim attivi che contengono due dichiarazioni esplicite
    riconoscibili. Non inventa contenuto: riusa valore e provenance esistenti."""
    repaired: list[UserClaim] = []
    for row in rows:
        value = row.get("value", "")
        if not _CLAUSE_SPLIT.search(value):
            continue
        prefix = {
            ("relation", "residenza"): "vivo a ",
            ("relation", "lavoro"): "lavoro come ",
        }.get((row.get("claim_type"), row.get("subject")))
        if prefix is None:
            continue
        repaired.extend(capture_explicit(
            prefix + value, provenance=list(row.get("provenance") or [])))
    return repaired
