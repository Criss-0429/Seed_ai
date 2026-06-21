"""Privacy gate: lite_mode (solo regex, niente modello ML) e unload-on-idle.
Offline: nessun modello reale; si inietta un fake engine per l'unload."""

from __future__ import annotations

import sys
import threading
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


class FakeGliner:
    """Imita GLiNER.predict_entities: trova un'email e un nome fissi."""
    def predict_entities(self, text, labels, threshold=0.5):
        out = []
        i = text.find("mario.rossi@example.com")
        if i >= 0:
            out.append({"start": i, "end": i + len("mario.rossi@example.com"),
                        "text": "mario.rossi@example.com", "label": "email"})
        j = text.find("Mario Rossi")
        if j >= 0:
            out.append({"start": j, "end": j + len("Mario Rossi"),
                        "text": "Mario Rossi", "label": "person"})
        return out


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
    g = _gate(backend="regex")
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


def test_close_stops_idle_watcher_and_releases_engine():
    g = _gate(idle_unload_s=1)
    g._opf_engine = FakeEngine()
    g._opf_tried = True
    g._start_idle_watch()
    watcher = g._opf_watch_thread

    assert watcher is not None and watcher.is_alive()
    g.close()

    assert not watcher.is_alive()
    assert g.opf_ready is False
    assert g.init_opf() is False
    assert not any(
        thread is watcher and thread.is_alive()
        for thread in threading.enumerate()
    )


def test_gliner_backend_detects_and_pseudonymizes():
    g = _gate(backend="gliner")
    g._opf_engine = FakeGliner()   # inietta il modello (gliner non installato in test)
    g._opf_tried = True
    out = g.redact("scrivi a Mario Rossi su mario.rossi@example.com", purpose="llm")
    assert "Mario Rossi" not in out.text
    assert "mario.rossi@example.com" not in out.text
    assert "[PERSON_1]" in out.text and "[EMAIL_1]" in out.text
    assert "gliner" in out.layers


def test_gliner_unavailable_degrades_to_regex():
    # gliner non installato -> load fallisce -> engine None -> solo regex
    g = _gate(backend="gliner")
    assert g.init_opf() is False
    out = g.redact("mail mario.rossi@example.com", purpose="llm")
    assert "mario.rossi@example.com" not in out.text   # regex copre comunque l'email
    assert "gliner" not in out.layers and "regex" in out.layers


def test_regex_backend_never_loads_model():
    g = _gate(backend="regex")
    assert g.init_opf() is False
    assert g._lite_mode is True
