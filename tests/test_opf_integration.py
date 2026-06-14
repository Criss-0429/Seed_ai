"""Test d'integrazione del Privacy Filter REALE (non mock).

Si esegue solo se `opf` e' installato e il checkpoint e' disponibile
(altrimenti skip pulito: la CI senza modello resta verde).

Eseguire con:  pytest tests/test_opf_integration.py -v -m opf
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.memory import Memory  # noqa: E402
from seed.core.privacy import PrivacyGate  # noqa: E402

opf = pytest.importorskip("opf", reason="OpenAI Privacy Filter non installato")


@pytest.fixture(scope="module")
def gate(tmp_path_factory):
    mem = Memory(tmp_path_factory.mktemp("opf") / "opf.db")
    g = PrivacyGate(mem)
    if not g.init_opf():
        pytest.skip("checkpoint OPF non disponibile (download fallito?)")
    return g


SAMPLES = [
    # (testo, frammenti che NON devono sopravvivere alla redazione)
    ("My name is John Carpenter and I live at 42 Maple Street, Boston.",
     ["John Carpenter", "42 Maple Street"]),
    ("Contact alice.smith@gmail.com or call +1 415 555 0134 about the account.",
     ["alice.smith@gmail.com", "555 0134"]),
    ("Mi chiamo Giulia Rossi e abito in via Garibaldi 12 a Torino.",
     ["Giulia Rossi"]),
    ("La mia API key e' sk-proj-abcd1234efgh5678ijkl e non va condivisa.",
     ["sk-proj-abcd1234efgh5678ijkl"]),
    ("Scrivi a mario.bianchi@azienda.it, il suo IBAN e' IT60X0542811101000000123456.",
     ["mario.bianchi@azienda.it", "IT60X0542811101000000123456"]),
]


class TestOPFReal:
    @pytest.mark.parametrize("text,must_disappear", SAMPLES,
                             ids=[f"sample{i}" for i in range(len(SAMPLES))])
    def test_pii_removed(self, gate, text, must_disappear):
        result = gate.redact(text)
        for fragment in must_disappear:
            assert fragment not in result.text, (
                f"PII sopravvissuta: {fragment!r} in {result.text!r}")
        assert "opf" in result.layers  # il layer modello ha girato davvero

    def test_placeholder_stability_across_calls(self, gate):
        r1 = gate.redact("Ho parlato con Marco Verdi del progetto.")
        r2 = gate.redact("Marco Verdi mi ha risposto ieri.")
        # lo stesso nome deve produrre lo stesso placeholder nelle due frasi
        ph1 = [t for t in r1.text.split() if t.startswith("[")]
        ph2 = [t for t in r2.text.split() if t.startswith("[")]
        common = set(ph1) & set(ph2)
        assert common, f"placeholder non stabile: {r1.text!r} vs {r2.text!r}"

    def test_rehydrate_roundtrip(self, gate):
        original = "Avvisa Laura Bruni della riunione."
        red = gate.redact(original)
        assert "Laura Bruni" not in red.text
        restored = gate.rehydrate(red.text)
        assert "Laura Bruni" in restored

    def test_clean_text_untouched_enough(self, gate):
        text = "Domani vorrei riorganizzare le cartelle del progetto."
        result = gate.redact(text)
        # niente PII: il testo deve restare sostanzialmente intatto
        assert "riorganizzare" in result.text and "progetto" in result.text
