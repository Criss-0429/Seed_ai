"""Finestra pywebview + bridge JS↔Python.

La UI e' lo strato 4 (mutabile): il renderer legge ui_manifest.json e si
ridisegna; questa shell (core) non cambia mai. Il permission broker usa
un dialog JS sincrono via webview.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
import sys
import threading

log = logging.getLogger("seed.ui")

_SURFACE = Path(__file__).resolve().parent / "surface"


def _start_overlay_hotkey(window) -> None:
    """Ctrl+Space globale Windows per evocare/ritirare l'overlay U6.

    Nessuna dipendenza esterna e nessuna osservazione del contesto: registra
    soltanto la scorciatoia. Il thread daemon muore col processo SEED.
    """
    if sys.platform != "win32":
        return

    def _listen() -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hotkey_id = 0x5344
        if not user32.RegisterHotKey(None, hotkey_id, 0x0002 | 0x4000, 0x20):
            log.warning("Ctrl+Spazio globale non registrato")
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message != 0x0312 or msg.wParam != hotkey_id:
                continue
            try:
                window.show()
                window.restore()
                window.evaluate_js("window.seedToggleOverlayFromHost()")
            except Exception as exc:
                log.warning("hotkey overlay fallito: %s", exc)

    threading.Thread(target=_listen, name="seed-overlay-hotkey", daemon=True).start()


class JsApi:
    """Metodi esposti a JavaScript (window.pywebview.api.*)."""

    def __init__(self, app):
        self._app = app
        self._window = None

    def attach(self, window) -> None:
        self._window = window
        # il broker chiede i permessi tramite dialog JS
        self._app.broker.set_ask_callback(self._ask_permission)

    # --- chat ----------------------------------------------------------
    def send_message(self, text: str) -> str:
        return self._app.handle_message(text)

    # --- stato UI --------------------------------------------------------
    def initial_state(self) -> dict:
        manifest = self._app.evolution.ui_manifest()
        onboarding = self._app.onboarding
        return {
            "onboarding_complete": onboarding.complete,
            "onboarding_phase": onboarding.state["phase"],
            "opening_prompt": onboarding.opening_prompt(),
            "greeting": manifest.get("persona", {}).get("greeting", "Sono qui."),
            "window_mode": "full",
        }

    def get_manifest(self) -> dict:
        return self._app.evolution.ui_manifest()

    def get_digest(self) -> dict:
        return self._app.evolution.pending_digest()

    def rollback(self, version: str, suppression_key: str = "") -> bool:
        return self._app.evolution.rollback(version, suppression_key)

    def list_versions(self) -> list:
        d = self._app.evolution.versions_dir
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.exists() else []

    # --- watcher / privacy ------------------------------------------------
    def watcher_pause(self, minutes: int) -> None:
        self._app.watcher.pause(minutes)

    def watcher_resume(self) -> None:
        self._app.watcher.resume()

    def watcher_status(self) -> dict:
        return {"paused": self._app.watcher.paused}

    # --- survey / report -----------------------------------------------------
    def submit_survey(self, usefulness: int, surprise: str) -> None:
        self._app.telemetry.record_survey(usefulness, surprise)

    def export_report(self) -> str:
        return str(self._app.export_report())

    # --- U2: Modello Utente + Permessi e Privacy ------------------------
    def user_model(self) -> list:
        return self._app.ui_user_model()

    def correct_claim(self, claim_id: int, is_true: bool, new_value: str = "") -> dict:
        return self._app.ui_correct_claim(claim_id, is_true, new_value)

    def permissions(self) -> dict:
        return self._app.ui_permissions()

    def explain_last(self) -> str:
        return self._app.ui_explain_last()

    def set_observation_consent(self, obs_class: str, enabled: bool) -> dict:
        return self._app.ui_set_observation_consent(obs_class, enabled)

    def revoke_observations(self) -> dict:
        return self._app.ui_revoke_observations()

    # --- orb state / daemon (U0/U1) -------------------------------------
    def daemon_status(self) -> dict:
        return self._app.run_daemon_review()

    # --- voice (facoltativo, U3) -----------------------------------------
    def voice_available(self) -> bool:
        return self._app.voice.available

    def grant_voice_consent(self, granted: bool = True) -> bool:
        return self._app.grant_voice_consent(granted)

    def voice_ready(self) -> bool:
        return self._app.voice_ready()

    def voice_message(self, audio_b64: str, mime: str = "audio/webm") -> dict:
        try:
            audio = base64.b64decode(audio_b64, validate=True)
        except (ValueError, TypeError):
            return {"error": "audio non valido"}
        if not audio or len(audio) > 20 * 1024 * 1024:
            return {"error": "audio vuoto o troppo grande"}
        return self._app.voice_message(audio, mime)

    def voice_reply_audio(self, text: str) -> dict:
        try:
            audio = self._app.voice_reply_audio(text)
        except Exception as exc:
            log.warning("TTS UI non disponibile: %s", exc)
            return {"error": str(exc)}
        return {
            "mime": "audio/mpeg",
            "audio_b64": base64.b64encode(audio).decode("ascii"),
        }

    # --- modalita' finestra (U5/U6) -------------------------------------
    def set_window_mode(self, mode: str) -> dict:
        if self._window is None:
            return {"ok": False, "mode": mode}
        modes = {
            "full": (900, 640, False),
            "presence": (420, 520, True),
            "overlay": (660, 116, True),
        }
        if mode not in modes:
            return {"ok": False, "mode": mode}
        width, height, on_top = modes[mode]
        try:
            self._window.restore()
            self._window.resize(width, height)
            self._window.on_top = on_top
            return {"ok": True, "mode": mode, "width": width, "height": height,
                    "on_top": on_top}
        except Exception as exc:
            log.warning("modalita' finestra %s fallita: %s", mode, exc)
            return {"ok": False, "mode": mode, "error": str(exc)}

    # --- permission dialog ----------------------------------------------------
    def _ask_permission(self, req) -> dict:
        if self._window is None:
            return {"decision": "deny", "remember": False}
        payload = json.dumps({"capability": req.capability_id,
                              "risk": req.risk_class,
                              "scope": req.scope,
                              "reason": req.reason})
        # seedAskPermission e' definita in renderer: mostra il dialog e
        # ritorna {"decision": ..., "remember": ...}
        try:
            result = self._window.evaluate_js(f"seedAskPermission({payload})")
            if isinstance(result, str):
                result = json.loads(result)
            return result or {"decision": "deny", "remember": False}
        except Exception as exc:
            log.error("permission dialog fallito: %s", exc)
            return {"decision": "deny", "remember": False}


def run_window(app) -> None:
    import webview  # pywebview

    api = JsApi(app)
    window = webview.create_window(
        "SEED", url=str(_SURFACE / "index.html"), js_api=api,
        width=900, height=640, min_size=(360, 82),
        background_color="#111111")
    api.attach(window)

    def _on_start():
        app.start_background()
        _start_overlay_hotkey(window)

    webview.start(_on_start, private_mode=False)
    app.shutdown()
