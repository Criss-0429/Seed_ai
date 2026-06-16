"""Test S11.2 emotion: segnale affettivo per-turno, graceful, solo voce,
mai memoria/diagnosi."""

from __future__ import annotations

import sys
import time
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.emotion import (  # noqa: E402
    AffectSignal,
    EmotionRecognizer,
    label_key,
)


# -- funzioni pure ----------------------------------------------------------

def test_label_key_normalizes_zh_and_en():
    assert label_key("开心") == "happy"
    assert label_key("ANGRY") == "angry"
    assert label_key("qualcosa") == "neutral"


def test_tone_hint_per_label():
    assert "giu'" in AffectSignal("sad", 0.9, "m", time.time()).tone_hint()
    assert "neutro" in AffectSignal("xyz", 0.9, "m", time.time()).tone_hint()


def test_affect_expires():
    assert AffectSignal("sad", 0.9, "m", time.time() - 1000).expired() is True
    assert AffectSignal("sad", 0.9, "m", time.time()).expired() is False


# -- recognizer -------------------------------------------------------------

def test_recognize_empty_audio_returns_none():
    assert EmotionRecognizer("x").recognize(b"") is None      # no model load


def test_recognizer_graceful_when_transformers_unavailable(monkeypatch):
    fake = types.ModuleType("transformers")

    def _raise(*a, **k):
        raise RuntimeError("transformers non disponibile")

    fake.pipeline = _raise
    monkeypatch.setitem(sys.modules, "transformers", fake)
    rec = EmotionRecognizer("x")
    assert rec.available is False
    assert rec.recognize(b"audio") is None


def _wav_bytes(sample_rate=16000):
    import io
    import numpy as np
    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, np.zeros(sample_rate, dtype="float32"), sample_rate, format="WAV")
    return buf.getvalue()


def test_recognize_with_stub_pipeline():
    rec = EmotionRecognizer("x")
    rec._tried = True
    rec._ok = True
    # pipeline e' un callable che ritorna [{label, score}] ordinato
    rec._model = lambda audio: [{"label": "happy", "score": 0.8}]
    sig = rec.recognize(_wav_bytes())
    assert sig is not None and label_key(sig.label) == "happy"
    assert sig.confidence == 0.8


def test_recognize_resamples_without_librosa():
    rec = EmotionRecognizer("x")
    rec._tried = True
    rec._ok = True
    captured = {}

    def pipeline(audio):
        captured.update(audio)
        return [{"label": "neutral", "score": 0.7}]

    rec._model = pipeline
    assert rec.recognize(_wav_bytes(8000)) is not None
    assert captured["sampling_rate"] == 16000
    assert len(captured["raw"]) == 16000


# -- iniezione nel system prompt (solo voce, temporaneo) --------------------

def test_affect_note_in_system_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    app = SeedApp(SeedConfig())
    decision = app.personality.plan("ciao", None)
    fresh = AffectSignal("sad", 0.9, "m", time.time())
    assert "SEGNALE AFFETTIVO" in app._system_prompt(decision, "ciao", fresh)
    # segnale scaduto -> nessuna nota (e' temporaneo)
    old = AffectSignal("sad", 0.9, "m", time.time() - 1000)
    assert "SEGNALE AFFETTIVO" not in app._system_prompt(decision, "ciao", old)
    # default (chat scritta): nessun affect
    assert "SEGNALE AFFETTIVO" not in app._system_prompt(decision, "ciao")
    app.shutdown()
