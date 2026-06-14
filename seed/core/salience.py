"""K3: gate di salienza deterministico e spiegabile per il contesto.

Non parla autonomamente e non chiama LLM. Decide solo se un elemento recuperato
da M3 entra nel prompt (`use_context`) o resta memoria silenziosa.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from . import recall

_DAY = 24 * 60 * 60


@dataclass(frozen=True)
class SalienceDecision:
    item_ref: str
    score: float
    reasons: tuple[str, ...]
    action: str
    factors: dict[str, float]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _item_ref(item: dict, fallback: str) -> str:
    if item.get("kid") is not None:
        return f"knowledge:{item['kid']}"
    if item.get("fact_id") is not None:
        return f"fact:{item['fact_id']}"
    return fallback


def _connected_to_seed(item: dict, seed_ids: set[int], edges: list[dict]) -> bool:
    kid = item.get("kid")
    if kid is None or not seed_ids:
        return False
    for edge in edges:
        if edge["source_id"] == kid and edge["target_id"] in seed_ids:
            return True
        if edge["target_id"] == kid and edge["source_id"] in seed_ids:
            return True
    return False


def score_item(query: str, item: dict, *, item_ref: str,
               graph_relevant: bool = False, edges: list[dict] | None = None,
               now: float | None = None) -> SalienceDecision:
    """Score iniziale K3. Rilevanza spiegabile obbligatoria per entrare."""
    now = now or time.time()
    overlap = recall.explain(query, item).get("overlap", 0)
    lexical = _clamp(float(overlap) / 2.0)
    relevance = max(lexical, 0.55 if graph_relevant else 0.0)
    provenance_count = len(item.get("provenance") or [])
    recurrence = _clamp(provenance_count / 3.0)
    age = max(0.0, now - float(item.get("created_at") or now))
    duration = _clamp(age / (90 * _DAY)) * recurrence
    novelty = _clamp(1.0 - recurrence)
    evidence = _clamp(item.get("confidence", 0.6))
    risk = {
        "boundary": 1.0, "exception": 0.7, "state": 0.5,
        "routine": 0.35,
    }.get(item.get("claim_type"), 0.2)
    sensitivity = 1.0 if item.get("sensitivity") == "sensitive" else 0.0
    stale = 1.0 if (
        item.get("lifecycle_state") not in (None, "active")
        or item.get("superseded_at") is not None
    ) else 0.0
    contradiction = 0.0
    kid = item.get("kid")
    for edge in edges or []:
        if kid in (edge.get("source_id"), edge.get("target_id")) \
                and edge.get("edge_type") in ("contradicts", "attenuates", "inhibits"):
            contradiction = max(contradiction, _clamp(edge.get("weight", 1.0)))

    score = _clamp(
        0.25 * relevance
        + 0.10 * recurrence
        + 0.05 * duration
        + 0.05 * novelty
        + 0.20 * evidence
        + 0.10                          # timing fit: richiesta interattiva corrente
        + 0.10 * risk
        - 0.30 * sensitivity
        - 0.30 * stale
        - 0.20 * contradiction
    )
    factors = {
        "relevance": relevance, "recurrence": recurrence, "duration": duration,
        "novelty": novelty, "evidence_strength": evidence, "risk_if_ignored": risk,
        "sensitivity_penalty": sensitivity, "stale_penalty": stale,
        "contradiction_penalty": contradiction,
    }
    reasons = [
        f"{name}={value:.2f}" for name, value in factors.items() if value > 0.0
    ]
    eligible = (
        relevance > 0.0
        and score >= 0.35
        and sensitivity == 0.0
        and stale == 0.0
        and contradiction < 0.75
        and item.get("lifecycle_state") not in ("candidate", "rejected")
    )
    return SalienceDecision(
        item_ref=item_ref, score=round(score, 4), reasons=tuple(reasons),
        action="use_context" if eligible else "remember_silently",
        factors=factors,
    )


def select_context(query: str, ranked: list[dict], *,
                   edges: list[dict] | None = None,
                   now: float | None = None) -> tuple[list[dict], list[SalienceDecision]]:
    """Filtra l'output M3. Senza segnale spiegabile non entra nulla."""
    edges = edges or []
    seed_ids = {
        item["kid"] for item in ranked
        if item.get("kid") is not None and recall.explain(query, item)["overlap"] > 0
    }
    selected: list[dict] = []
    decisions: list[SalienceDecision] = []
    for idx, item in enumerate(ranked):
        decision = score_item(
            query, item, item_ref=_item_ref(item, f"retrieved:{idx}"),
            graph_relevant=_connected_to_seed(item, seed_ids, edges),
            edges=edges, now=now)
        decisions.append(decision)
        if decision.action == "use_context":
            selected.append(item)
    return selected, decisions


def select_counterpoint(query: str, fragments: list[dict]) -> list[dict]:
    """Counterpoint approvato entra solo se topic/reason ha match spiegabile."""
    selected = []
    for fragment in fragments:
        item = {"statement": f"{fragment.get('topic', '')} {fragment.get('reason', '')}"}
        if recall.explain(query, item)["overlap"] > 0:
            selected.append(fragment)
    return selected
