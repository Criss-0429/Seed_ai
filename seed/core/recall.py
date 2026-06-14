"""M1 selezione della conoscenza per rilevanza: deterministica, zero token.

Principio canonico (wiki `Jarvis_User_Knowledge_Ontology` /
`Jarvis_Cognitive_User_Model_Execution_Harness`): "usa la conoscenza solo quando
e' rilevante"; "se manca spiegazione, non entra nel workspace". Qui implemento la
fetta deterministica del retrieval: overlap lessicale con la richiesta corrente +
recency. Spiegabile: ogni elemento porta il suo punteggio e i token che hanno
fatto match. L'arricchimento semantico (vettori, graph proximity) arriva in M3.
"""

from __future__ import annotations

import re
import time
from typing import Any

_TOKEN = re.compile(r"\w+", re.UNICODE)

# Stopword italiane/inglesi minime: non portano segnale di rilevanza.
_STOP = frozenset({
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da",
    "in", "con", "su", "per", "tra", "fra", "e", "ed", "o", "ma", "se", "che",
    "chi", "cui", "non", "ne", "ci", "si", "mi", "ti", "vi", "come", "cosa",
    "dove", "quando", "perche", "quale", "quali", "sono", "sei", "essere",
    "ho", "hai", "ha", "io", "tu", "lui", "lei", "noi", "voi", "loro", "del",
    "della", "dei", "delle", "al", "alla", "ai", "alle", "nel", "nella",
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "you", "your", "my", "me", "i", "it", "this", "that",
})

_RECENCY_HALF_LIFE_S = 60 * 60 * 24 * 30   # ~un mese


def _tokens(text: str) -> set[str]:
    return {
        t for t in (m.group(0).lower() for m in _TOKEN.finditer(text))
        if len(t) > 2 and t not in _STOP
    }


def select_relevant(query: str, items: list[dict], *, k: int = 8,
                    text_key: str = "statement", min_overlap: int = 1,
                    now: float | None = None) -> list[dict]:
    """Ritorna fino a `k` item pertinenti alla query, piu' rilevanti prima.
    Un item entra solo se condivide almeno `min_overlap` token con la query
    (rilevanza, non dump). `created_at` opzionale da' un piccolo boost recency."""
    qt = _tokens(query or "")
    if not qt:
        return []
    now = now or time.time()
    scored: list[tuple[float, int, dict]] = []
    for idx, item in enumerate(items):
        overlap = len(qt & _tokens(str(item.get(text_key, ""))))
        if overlap < min_overlap:
            continue
        recency = 0.0
        ts = item.get("created_at")
        if ts:
            age = max(0.0, now - float(ts))
            recency = max(0.0, 1.0 - age / _RECENCY_HALF_LIFE_S)
        score = overlap + 0.3 * recency
        scored.append((score, -idx, item))     # -idx: stabile, preferisce i primi
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [item for _, _, item in scored[:k]]


def explain(query: str, item: dict, *, text_key: str = "statement") -> dict[str, Any]:
    """Motivo della selezione (audit/spiegabilita'): token in comune."""
    shared = sorted(_tokens(query or "") & _tokens(str(item.get(text_key, ""))))
    return {"matched_tokens": shared, "overlap": len(shared)}
