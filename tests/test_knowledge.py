"""Test M2 conoscenza tipata: contratto, supersession/contradiction
(anti-staleness), estrazione candidate-only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.knowledge import (  # noqa: E402
    KnowledgeError,
    KnowledgeExtractor,
    KnowledgeStore,
    UserClaim,
)
from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.memory import Memory  # noqa: E402


def _store(tmp_path):
    mem = Memory(tmp_path / "k.db")
    return KnowledgeStore(mem), mem


# -- contratto --------------------------------------------------------------

def test_invalid_claim_type_rejected():
    with pytest.raises(KnowledgeError):
        UserClaim("nontype", "x", "y").validate()


def test_inferred_confidence_is_capped():
    c = UserClaim("state", "umore", "stanco", confidence=0.95,
                  confidence_source="inferred").normalized()
    assert c.confidence <= 0.45


def test_hypothesis_cannot_be_explicit():
    c = UserClaim("hypothesis", "x", "y", confidence_source="explicit").normalized()
    assert c.confidence_source == "inferred"      # ipotesi mai esplicita


# -- store: add / noop ------------------------------------------------------

def test_explicit_claim_becomes_active(tmp_path):
    store, mem = _store(tmp_path)
    out = store.record(UserClaim("relation", "residenza", "Milano",
                                 confidence_source="explicit"))
    assert out["action"] == "added" and out["lifecycle"] == "active"
    assert len(mem.active_knowledge()) == 1
    mem.close()


def test_inferred_claim_stays_candidate(tmp_path):
    store, mem = _store(tmp_path)
    out = store.record(UserClaim("state", "umore", "stanco",
                                 confidence_source="inferred"))
    assert out["lifecycle"] == "candidate"
    assert mem.active_knowledge() == []           # candidate non e' attivo
    mem.close()


def test_same_value_is_noop(tmp_path):
    store, mem = _store(tmp_path)
    store.record(UserClaim("relation", "residenza", "Milano"))
    out = store.record(UserClaim("relation", "residenza", "Milano"))
    assert out["action"] == "noop"
    assert len(mem.all_knowledge()) == 1          # nessun duplicato
    mem.close()


# -- anti-staleness: supersession -------------------------------------------

def test_new_explicit_value_supersedes_old(tmp_path):
    """Il caso 'dark mode poi light mode': il vecchio NON resta attivo."""
    store, mem = _store(tmp_path)
    store.record(UserClaim("preference", "tema_ui", "dark"))
    store.record(UserClaim("preference", "tema_ui", "light"))
    active = mem.active_knowledge()
    assert len(active) == 1
    assert active[0]["value"] == "light"
    superseded = [r for r in mem.all_knowledge() if r["lifecycle_state"] == "superseded"]
    assert len(superseded) == 1 and superseded[0]["value"] == "dark"
    mem.close()


def test_inferred_does_not_override_explicit_fact(tmp_path):
    store, mem = _store(tmp_path)
    store.record(UserClaim("relation", "residenza", "Milano",
                           confidence_source="explicit"))
    out = store.record(UserClaim("relation", "residenza", "Roma",
                                 confidence_source="inferred"))
    assert out["lifecycle"] == "candidate"        # inferenza non supera il fatto
    active = mem.active_knowledge()
    assert len(active) == 1 and active[0]["value"] == "Milano"
    mem.close()


# -- estrazione candidate-only ----------------------------------------------

class FakeLLM:
    configured = True

    def __init__(self, payload):
        self.payload = payload

    def chat(self, messages, **kw):
        return LLMResponse(text=json.dumps(self.payload))


def test_extractor_parses_typed_candidates():
    llm = FakeLLM({"claims": [
        {"claim_type": "relation", "subject": "lavoro", "value": "sviluppatore",
         "confidence_source": "explicit"},
        {"claim_type": "hypothesis", "subject": "x", "value": "y",
         "confidence_source": "inferred"},
    ]})
    claims = KnowledgeExtractor().extract("user: faccio lo sviluppatore", llm)
    assert len(claims) == 2
    assert claims[0].claim_type == "relation"


def test_extractor_skips_malformed_claims():
    llm = FakeLLM({"claims": [
        {"claim_type": "nonexistent", "subject": "x", "value": "y"},
        {"subject": "no_type"},
        {"claim_type": "fact", "subject": "ok", "value": "v",
         "confidence_source": "explicit"},
    ]})
    claims = KnowledgeExtractor().extract("testo", llm)
    assert len(claims) == 1 and claims[0].subject == "ok"


def test_extractor_no_llm_returns_empty():
    assert KnowledgeExtractor().extract("testo", None) == []


def test_extractor_end_to_end_into_store(tmp_path):
    store, mem = _store(tmp_path)
    llm = FakeLLM({"claims": [
        {"claim_type": "routine", "subject": "palestra", "value": "mercoledi",
         "confidence_source": "explicit"}]})
    for claim in KnowledgeExtractor().extract("user: vado in palestra il mercoledi", llm):
        store.record(claim)
    active = mem.active_knowledge(claim_type="routine")
    assert len(active) == 1 and active[0]["value"] == "mercoledi"
    mem.close()
