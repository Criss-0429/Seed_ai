"""BYOK ElevenLabs per la voce: FACOLTATIVO e skippabile.

La voce (STT/TTS) e' una feature opzionale. SEED resta pienamente usabile in
modalita' testuale senza alcuna key ElevenLabs. Quando l'utente vuole la voce,
inserisce la propria key: viene validata sul provider, cifrata con DPAPI (come il
Provider Hub) e salvata SOLO sotto ``core_config``. L'utente puo' anche saltare:
in quel caso la voce resta spenta e non viene piu' riproposta come bloccante.

Il file persistito contiene solo metadati e ciphertext, mai la key in chiaro.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import requests

from . import forbidden
from .dpapi import decrypt_str, encrypt_str
from .jsonio import write_json_atomic

SCHEMA_VERSION = "seed.voice-credentials.v1"
_API = "https://api.elevenlabs.io/v1"


class VoiceCredentialsError(RuntimeError):
    pass


def voice_credentials_path() -> Path:
    return forbidden.core_config_dir() / "voice_credentials.json"


class VoiceCredentials:
    """Store opzionale per la key ElevenLabs (BYOK voce)."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        request: Callable[..., Any] | None = None,
        audit: Callable[[str, dict], None] | None = None,
    ):
        self.path = path or voice_credentials_path()
        self._request = request or requests.request
        self._audit = audit

    # -- stato ------------------------------------------------------------
    def status(self) -> dict:
        data = self._load()
        configured = bool(data.get("key_dpapi"))
        return {
            "schema_version": SCHEMA_VERSION,
            "provider": "elevenlabs",
            "optional": True,
            "configured": configured,
            "validated": bool(data.get("validated_at")),
            "validated_at": data.get("validated_at"),
            "skipped": bool(data.get("skipped")),
            "available": configured,
            "dashboard_url": "https://elevenlabs.io/app/settings/api-keys",
        }

    @property
    def available(self) -> bool:
        return bool(self._load().get("key_dpapi"))

    def api_key(self) -> str:
        data = self._load()
        cipher = data.get("key_dpapi")
        return decrypt_str(cipher) if cipher else ""

    # -- mutazioni --------------------------------------------------------
    def validate_and_save(self, api_key: str) -> dict:
        api_key = (api_key or "").strip()
        if not api_key:
            raise VoiceCredentialsError("API key richiesta")
        self._validate_key(api_key)
        data = self._load()
        data["key_dpapi"] = encrypt_str(api_key)
        data["validated_at"] = time.time()
        data["skipped"] = False
        self._save(data)
        self._record("voice_key_validated", True)
        return self.status()

    def skip(self) -> dict:
        """L'utente rinuncia alla voce: nessuna key, non piu' riproposta."""
        data = self._load()
        data["skipped"] = True
        self._save(data)
        self._record("voice_key_skipped", True)
        return self.status()

    def revoke(self) -> dict:
        data = self._load()
        data.pop("key_dpapi", None)
        data["validated_at"] = None
        data["skipped"] = False
        self._save(data)
        self._record("voice_key_revoked", True)
        return self.status()

    # -- interni ----------------------------------------------------------
    def _validate_key(self, api_key: str) -> None:
        try:
            response = self._request(
                "GET", f"{_API}/user", headers={"xi-api-key": api_key}, timeout=30
            )
            response.raise_for_status()
        except Exception as exc:  # rete o 401: key non valida
            self._record("voice_key_validation_failed", False)
            raise VoiceCredentialsError(f"key ElevenLabs non valida: {exc}") from exc

    def _load(self) -> dict:
        if not self.path.exists():
            return {"schema_version": SCHEMA_VERSION, "skipped": False}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise VoiceCredentialsError("invalid voice credentials store")
        return data

    def _save(self, data: dict) -> None:
        data["schema_version"] = SCHEMA_VERSION
        write_json_atomic(self.path, data)

    def _record(self, event: str, ok: bool) -> None:
        if self._audit:
            self._audit(event, {"provider": "elevenlabs", "ok": ok})
