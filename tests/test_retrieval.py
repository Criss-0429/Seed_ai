"""Test M3 retrieval triple-stream + RRF + edge semantici.
Lexical+graph deterministici (no embedder, no download)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.knowledge import KnowledgeStore, UserClaim  # noqa: E402
from seed.core.memory import Memory  # noqa: E402
from seed.core.retrieval import rank_candidates, rrf_fuse  # noqa: E402


# -- RRF --------------------------------------------------------------------

def test_rrf_fuse_orders_by_reciprocal_rank():
    fused = rrf_fuse([[1, 2, 3], [3, 1, 2]])
    assert set(fused) == {1, 2, 3}
    assert fused[0] == 1                 # primo in entrambi i ranking vicino al top


def test_rrf_empty():
    assert rrf_fuse([]) == []


# -- rank_candidates --------------------------------------------------------

def test_lexical_only_selects_relevant():
    cands = [{"statement": "progetto unreal engine", "kid": None},
             {"statement": "che tempo fa domani", "kid": None}]
    out = rank_candidates("dimmi del progetto unreal", cands, k=5)
    assert len(out) == 1 and "unreal" in out[0]["statement"]


def test_graph_stream_pulls_in_connected_claim():
    # kid=1 matcha lessicalmente; kid=2 no, ma e' collegato a 1 da un edge.
    cands = [{"statement": "progetto unreal engine", "kid": 1},
             {"statement": "motore grafico avanzato", "kid": 2}]
    edges = [{"source_id": 1, "target_id": 2, "weight": 1.0}]
    out = rank_candidates("dimmi del progetto", cands, edges=edges, k=5)
    kids = {c["kid"] for c in out}
    assert kids == {1, 2}                 # 2 entra via grafo, non via lessico


def test_empty_candidates():
    assert rank_candidates("q", [], k=5) == []


def test_no_signal_returns_empty():
    cands = [{"statement": "argomento totalmente diverso", "kid": None}]
    assert rank_candidates("xyzzy", cands, k=5) == []


# -- edge su supersession ---------------------------------------------------

def test_supersession_creates_supersedes_edge(tmp_path):
    mem = Memory(tmp_path / "e.db")
    store = KnowledgeStore(mem)
    store.record(UserClaim("preference", "tema_ui", "dark"))
    store.record(UserClaim("preference", "tema_ui", "light"))
    edges = mem.all_edges()
    assert len(edges) == 1
    assert edges[0]["edge_type"] == "supersedes"
    # source = nuovo (light), target = vecchio (dark)
    active = mem.active_knowledge()[0]
    assert edges[0]["source_id"] == active["id"]
    mem.close()


def test_edges_for_node(tmp_path):
    mem = Memory(tmp_path / "e2.db")
    mem.add_edge(source_id=10, target_id=20, edge_type="supports")
    assert len(mem.edges_for(10)) == 1
    assert len(mem.edges_for(20)) == 1
    assert mem.edges_for(99) == []
    mem.close()
