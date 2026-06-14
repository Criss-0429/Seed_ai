"""Test S11.1 voce: STT/TTS adapter, fallback, budget, consenso, audit.
Offline: requests.post mockato, nessuna chiamata reale."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import voice as voice_mod  # noqa: E402
from seed.core.config import VoiceConfig  # noqa: E402
from seed.core.memory import Memory  # noqa: E402
from seed.core.voice import VoiceBudgetError, VoiceEngine, VoiceError  # noqa: E402


class FakeResp:
    def __init__(self, *, json_data=None, content=b"audio", status=200):
        self._json = json_data
        self.content = content
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"http {self.status}")

    def json(self):
        return self._json


def _audit():
    events = []
    return events, lambda ev, p: events.append((ev, p))


def _cfg(**kw):
    base = dict(elevenlabs_api_key="k", enabled=True)
    base.update(kw)
    return VoiceConfig(**base)


# -- gating -----------------------------------------------------------------

def test_disabled_without_key():
    eng = VoiceEngine(VoiceConfig(elevenlabs_api_key="", enabled=True))
    assert eng.enabled is False
    with pytest.raises(VoiceError):
        eng.speak("ciao")


def test_voice_id_gender_and_override():
    eng = VoiceEngine(_cfg(voice_id_female="F", voice_id_male="M", active_voice="male"))
    assert eng.voice_id_for() == "M"
    assert eng.voice_id_for("female") == "F"
    eng2 = VoiceEngine(_cfg(voice_id="OVERRIDE", voice_id_male="M"))
    assert eng2.voice_id_for("male") == "OVERRIDE"      # override vince


# -- STT --------------------------------------------------------------------

def test_transcribe_returns_text_and_audits(monkeypatch):
    events, audit = _audit()
    monkeypatch.setattr(voice_mod.requests, "post", lambda *a, **k: FakeResp(
        json_data={"text": "ciao mondo", "language_code": "ita",
                   "language_probability": 0.9}))
    eng = VoiceEngine(_cfg(), audit=audit)
    out = eng.transcribe(b"xxx")
    assert out["text"] == "ciao mondo" and out["language"] == "ita"
    kind, payload = events[0]
    assert kind == "voice_stt" and payload["ok"] is True
    assert "ciao mondo" not in str(payload)            # mai transcript nell'audit


def test_transcribe_rejects_oversize_audio():
    eng = VoiceEngine(_cfg(max_audio_bytes=10))
    with pytest.raises(VoiceError):
        eng.transcribe(b"x" * 50)


# -- TTS --------------------------------------------------------------------

def test_speak_success_tracks_chars(monkeypatch):
    events, audit = _audit()
    monkeypatch.setattr(voice_mod.requests, "post",
                        lambda *a, **k: FakeResp(content=b"mp3"))
    eng = VoiceEngine(_cfg(), audit=audit)
    assert eng.speak("ciao") == b"mp3"
    assert events[-1][0] == "voice_tts" and events[-1][1]["ok"] is True
    assert events[-1][1]["fallback"] is False


def test_speak_falls_back_on_primary_error(monkeypatch):
    events, audit = _audit()
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("primary down")
        return FakeResp(content=b"mp3-fallback")

    monkeypatch.setattr(voice_mod.requests, "post", fake_post)
    eng = VoiceEngine(_cfg(), audit=audit)
    assert eng.speak("ciao") == b"mp3-fallback"
    assert events[-1][1]["fallback"] is True and events[-1][1]["ok"] is True


def test_speak_budget_exceeded(monkeypatch):
    monkeypatch.setattr(voice_mod.requests, "post",
                        lambda *a, **k: FakeResp(content=b"mp3"))
    eng = VoiceEngine(_cfg(monthly_char_cap=3))
    with pytest.raises(VoiceBudgetError):
        eng.speak("troppo lungo")


# -- consenso ---------------------------------------------------------------

def test_memory_voice_consent_roundtrip(tmp_path):
    mem = Memory(tmp_path / "v.db")
    assert mem.voice_consent() is False
    mem.set_voice_consent(True)
    assert mem.voice_consent() is True
    mem.set_voice_consent(False)
    assert mem.voice_consent() is False
    mem.close()
