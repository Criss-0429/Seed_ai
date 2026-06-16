"""STT/TTS via ElevenLabs — FACOLTATIVI. Key vuota = modulo spento, SEED testuale.

Il microfono si attiva SOLO premendo il tasto voce nella UI: niente ascolto ambientale.
L'audio registrato va a ElevenLabs per la trascrizione SOLO previo consenso
(risk_class network, gestito dal permission broker alla prima attivazione).
Il testo trascritto rientra nel flusso normale e passa dal privacy gate
prima di raggiungere l'LLM.
"""

from __future__ import annotations

import logging

import requests

log = logging.getLogger("seed.voice")

_API = "https://api.elevenlabs.io/v1"


class VoiceEngine:
    def __init__(self, api_key: str, voice_id: str = "", enabled: bool = False):
        self._key = api_key
        self.voice_id = voice_id
        self.enabled = enabled and bool(api_key)

    @property
    def available(self) -> bool:
        return bool(self._key)

    def transcribe(self, audio_bytes: bytes, mime: str = "audio/webm") -> str:
        """STT (ElevenLabs Scribe). Ritorna il testo grezzo: il chiamante DEVE
        passarlo dal privacy gate prima di usarlo verso l'LLM."""
        if not self.enabled:
            raise RuntimeError("voice non attiva (key mancante o disattivata)")
        resp = requests.post(
            f"{_API}/speech-to-text",
            headers={"xi-api-key": self._key},
            files={"file": ("audio", audio_bytes, mime)},
            data={"model_id": "scribe_v1"},
            timeout=60)
        resp.raise_for_status()
        return resp.json().get("text", "")

    def speak(self, text: str) -> bytes:
        """TTS: il testo in ingresso e' quello GIA' re-idratato mostrato all'utente
        (va a ElevenLabs: l'utente lo sa dal consenso voice). Ritorna mp3 bytes."""
        if not self.enabled:
            raise RuntimeError("voice non attiva")
        voice = self.voice_id or "21m00Tcm4TlvDq8ikWAM"
        resp = requests.post(
            f"{_API}/text-to-speech/{voice}",
            headers={"xi-api-key": self._key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=60)
        resp.raise_for_status()
        return resp.content
