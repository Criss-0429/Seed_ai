"""BYOK ElevenLabs (voce, facoltativo): validazione mockata, skip, revoca, cifratura.
Offline: nessuna chiamata reale; DPAPI e' no-op fuori da Windows."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.voice_credentials import (  # noqa: E402
    VoiceCredentials,
    VoiceCredentialsError,
)


class FakeResp:
    def __init__(self, status=200):
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"http {self.status}")


def _store(tmp_path, request=None):
    events = []
    return (
        VoiceCredentials(
            tmp_path / "voice_credentials.json",
            request=request,
            audit=lambda ev, p: events.append((ev, p)),
        ),
        events,
    )


def test_empty_store_is_optional_and_skippable(tmp_path):
    vc, _ = _store(tmp_path)
    st = vc.status()
    assert st["optional"] is True
    assert st["configured"] is False
    assert st["available"] is False
    assert st["skipped"] is False
    assert vc.api_key() == ""


def test_validate_and_save_roundtrip(tmp_path):
    vc, events = _store(tmp_path, request=lambda *a, **k: FakeResp(200))
    st = vc.validate_and_save("xi-secret-key")
    assert st["configured"] is True and st["validated"] is True
    assert st["skipped"] is False
    # la key torna decifrata, ma NON e' mai in chiaro nel file
    assert vc.api_key() == "xi-secret-key"
    raw = (tmp_path / "voice_credentials.json").read_text(encoding="utf-8")
    assert "xi-secret-key" not in raw
    assert ("voice_key_validated", {"provider": "elevenlabs", "ok": True}) in events


def test_empty_key_rejected(tmp_path):
    vc, _ = _store(tmp_path, request=lambda *a, **k: FakeResp(200))
    with pytest.raises(VoiceCredentialsError):
        vc.validate_and_save("   ")


def test_invalid_key_raises_and_not_saved(tmp_path):
    vc, events = _store(tmp_path, request=lambda *a, **k: FakeResp(401))
    with pytest.raises(VoiceCredentialsError):
        vc.validate_and_save("bad")
    assert vc.available is False
    assert ("voice_key_validation_failed", {"provider": "elevenlabs", "ok": False}) in events


def test_skip_marks_skipped_without_key(tmp_path):
    vc, _ = _store(tmp_path)
    st = vc.skip()
    assert st["skipped"] is True
    assert st["configured"] is False
    assert vc.api_key() == ""


def test_revoke_clears_key(tmp_path):
    vc, _ = _store(tmp_path, request=lambda *a, **k: FakeResp(200))
    vc.validate_and_save("xi-secret-key")
    st = vc.revoke()
    assert st["configured"] is False
    assert st["validated"] is False
    assert vc.api_key() == ""
