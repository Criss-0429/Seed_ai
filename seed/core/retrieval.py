"""M3 retrieval triple-stream con Reciprocal Rank Fusion (RRF).

Combina tre segnali (doc 14, agentmemory): lexical (M1, overlap), vector
(embedder locale opzionale, cosine) e graph proximity (claim collegati via edge
tipati ai seed lessicali). Fusione RRF (K=60): unisce ranking eterogenei senza
calibrare i punteggi. Esplicabile: ogni stream e' un ranking ispezionabile.

Degrada con grazia: senza embedder usa lexical+graph; senza edge usa lexical
(+vector). Almeno il lessicale e' sempre disponibile.
"""

from __future__ import annotations

from . import recall

_RRF_K = 60


def rrf_fuse(rankings: list[list[int]], k: int = _RRF_K) -> list[int]:
    """Fonde piu' ranking (liste di chiavi, best-first) in un ordine unico."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda key: scores[key], reverse=True)


def _graph_stream(candidates: list[dict], lexical_positions: list[int],
                  edges: list[dict]) -> list[int]:
    """Posizioni dei candidati collegati (via edge) ai seed lessicali, ordinate
    per peso dell'edge. Usa la chiave 'kid' (knowledge id) dei candidati."""
    id_to_pos = {c["kid"]: p for p, c in enumerate(candidates)
                 if c.get("kid") is not None}
    seeds = {candidates[p].get("kid") for p in lexical_positions[:3]
             if candidates[p].get("kid") is not None}
    if not seeds or not id_to_pos:
        return []
    weights: dict[int, float] = {}
    for e in edges:
        s, t, w = e["source_id"], e["target_id"], e["weight"]
        for a, b in ((s, t), (t, s)):
            if a in seeds and b in id_to_pos and b not in seeds:
                pos = id_to_pos[b]
                weights[pos] = max(weights.get(pos, 0.0), w)
    return sorted(weights, key=lambda p: weights[p], reverse=True)


def rank_candidates(query: str, candidates: list[dict], *,
                    edges: list[dict] | None = None, embedder=None,
                    k: int = 8, text_key: str = "statement") -> list[dict]:
    """Ritorna fino a `k` candidati piu' rilevanti, fusi via RRF dei tre stream.
    `candidates`: dict con `text_key` e, per il grafo, `kid` (knowledge id)."""
    if not candidates:
        return []
    pos_of = {id(c): p for p, c in enumerate(candidates)}
    rankings: list[list[int]] = []

    # stream lessicale (M1)
    lex = recall.select_relevant(query, candidates, k=len(candidates),
                                 text_key=text_key)
    lex_positions = [pos_of[id(c)] for c in lex]
    if lex_positions:
        rankings.append(lex_positions)

    # stream vettoriale (opzionale)
    if embedder is not None:
        order = embedder.rank(query, [str(c.get(text_key, "")) for c in candidates])
        if order:
            rankings.append(order)

    # stream grafo (proximita' agli edge)
    if edges and lex_positions:
        graph = _graph_stream(candidates, lex_positions, edges)
        if graph:
            rankings.append(graph)

    if not rankings:
        return []
    fused = rrf_fuse(rankings)
    return [candidates[p] for p in fused[:k]]
