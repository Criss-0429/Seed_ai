"""S11 STT/TTS via ElevenLabs — FACOLTATIVI. Key vuota = modulo spento, SEED testuale.

Microfono attivo SOLO premendo il tasto voce nella UI: niente ascolto ambientale.
L'audio va a ElevenLabs SOLO previo consenso voce esplicito (separato dal consenso
memoria). Il testo trascritto rientra nel flusso normale e passa dal privacy gate
prima di raggiungere l'LLM.

Retention minima: audio e transcript non persistono per default. L'audit registra
solo aggregati (modello, esito, durata, caratteri), MAI audio o testo.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

import requests

from .config import VoiceConfig

log = logging.getLogger("seed.voice")

_API = "https://api.elevenlabs.io/v1"


class VoiceError(RuntimeError):
    pass


class VoiceBudgetError(VoiceError):
    pass


class VoiceEngine:
    def __init__(self, cfg: VoiceConfig,
                 audit: Callable[[str, dict], None] | None = None):
        self._cfg = cfg
        self._key = cfg.elevenlabs_api_key
        self.enabled = cfg.enabled and bool(self._key)
        self._audit = audit
        self._chars_used = 0

    @property
    def available(self) -> bool:
        return bool(self._key)

    def _emit(self, event: str, payload: dict) -> None:
        if self._audit is not None:
            self._audit(event, payload)

    def voice_id_for(self, gender: str | None = None) -> str:
        if self._cfg.voice_id:                       # override esplicito
            return self._cfg.voice_id
        g = gender or self._cfg.active_voice
        return self._cfg.voice_id_male if g == "male" else self._cfg.voice_id_female

    # -- STT --------------------------------------------------------------
    def transcribe(self, audio_bytes: bytes, mime: str = "audio/webm") -> dict:
        """STT (Scribe). Ritorna {text, language, confidence}. Il chiamante DEVE
        passare `text` dal privacy gate prima di usarlo verso l'LLM."""
        if not self.enabled:
            raise VoiceError("voce non attiva (key mancante o disattivata)")
        if len(audio_bytes) > self._cfg.max_audio_bytes:
            raise VoiceError("audio troppo grande per la trascrizione")
        t0 = time.time()
        try:
            resp = requests.post(
                f"{_API}/speech-to-text",
                headers={"xi-api-key": self._key},
                files={"file": ("audio", audio_bytes, mime)},
                data={"model_id": self._cfg.stt_model},
                timeout=self._cfg.timeout_s)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            self._emit("voice_stt", {"ok": False, "model": self._cfg.stt_model,
                                     "bytes": len(audio_bytes),
                                     "ms": int((time.time() - t0) * 1000)})
            raise VoiceError(f"STT fallita: {exc}") from exc
        self._emit("voice_stt", {"ok": True, "model": self._cfg.stt_model,
                                 "bytes": len(audio_bytes),
                                 "ms": int((time.time() - t0) * 1000)})
        return {
            "text": data.get("text", ""),
            "language": data.get("language_code", ""),
            "confidence": data.get("language_probability"),
        }

    # -- TTS --------------------------------------------------------------
    def speak(self, text: str, *, gender: str | None = None) -> bytes:
        """TTS sul testo GIA' re-idratato mostrato all'utente. `eleven_v3`
        supporta audio tag espressivi ([laughs], [sigh], [thoughtful]...).
        Fallback automatico al modello stabile su errore. Ritorna mp3 bytes."""
        if not self.enabled:
            raise VoiceError("voce non attiva")
        chars = len(text or "")
        if self._chars_used + chars > self._cfg.monthly_char_cap:
            self._emit("voice_tts", {"ok": False, "reason": "budget",
                                     "chars": chars})
            raise VoiceBudgetError("budget TTS mensile esaurito")
        voice = self.voice_id_for(gender)
        for model, is_fallback in ((self._cfg.tts_model, False),
                                   (self._cfg.tts_fallback_model, True)):
            t0 = time.time()
            try:
                resp = requests.post(
                    f"{_API}/text-to-speech/{voice}",
                    headers={"xi-api-key": self._key, "Content-Type": "application/json"},
                    json={"text": text, "model_id": model},
                    timeout=self._cfg.timeout_s)
                resp.raise_for_status()
            except Exception as exc:
                self._emit("voice_tts", {"ok": False, "model": model,
                                         "fallback": is_fallback, "chars": chars,
                                         "ms": int((time.time() - t0) * 1000)})
                if is_fallback:
                    raise VoiceError(f"TTS fallita: {exc}") from exc
                log.warning("TTS %s fallita, provo fallback: %s", model, exc)
                continue
            self._chars_used += chars
            self._emit("voice_tts", {"ok": True, "model": model,
                                     "fallback": is_fallback, "chars": chars,
                                     "ms": int((time.time() - t0) * 1000)})
            return resp.content
        raise VoiceError("TTS non riuscita")          # unreachable
