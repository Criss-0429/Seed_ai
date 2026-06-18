"""Privacy gate: lite_mode (solo regex, niente modello ML) e unload-on-idle.
Offline: nessun modello reale; si inietta un fake engine per l'unload."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.privacy import PrivacyGate  # noqa: E402


class FakeMemory:
    def pii_map_lookup(self, value):
        return None

    def pii_map_count(self, label):
        return 0

    def pii_map_store(self, *a):
        pass

    def pii_map_all(self):
        return []


class FakeEngine:
    def redact(self, text):
        return text  # mai chiamato nei test di unload


def _gate(**kw):
    return PrivacyGate(FakeMemory(), **kw)


def test_lite_mode_never_loads_model():
    g = _gate(lite_mode=True)
    assert g.init_opf() is False
    assert g.opf_ready is False
    # redazione funziona comunque via regex
    out = g.redact("scrivimi a mario.rossi@example.com", purpose="llm")
    assert "mario.rossi@example.com" not in out.text
    assert "opf" not in out.layers and "regex" in out.layers


def test_regex_still_redacts_without_model():
    g = _gate()  # opf non installato in test -> engine None
    out = g.redact("IBAN IT60X0542811101000000123456 e +39 333 1234567",
                   purpose="llm")
    assert "IT60X0542811101000000123456" not in out.text
    assert "3331234567" not in out.text.replace(" ", "")


def test_idle_unload_frees_engine_after_threshold():
    g = _gate(idle_unload_s=1)
    g._opf_engine = FakeEngine()
    g._opf_tried = True
    g._opf_last_use = time.monotonic() - 5   # idle da 5s, soglia 1s
    assert g._maybe_unload() is True
    assert g._opf_engine is None
    assert g._opf_tried is False   # reload lazy abilitato


def test_idle_unload_keeps_engine_when_recently_used():
    g = _gate(idle_unload_s=120)
    g._opf_engine = FakeEngine()
    g._opf_last_use = time.monotonic()   # appena usato
    assert g._maybe_unload() is False
    assert g._opf_engine is not None


def test_idle_unload_disabled_when_zero():
    g = _gate(idle_unload_s=0)
    g._opf_engine = FakeEngine()
    g._opf_last_use = time.monotonic() - 9999
    assert g._maybe_unload() is False
    assert g._opf_engine is not None
