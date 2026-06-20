"""Finestra pywebview + bridge JS↔Python.

La UI e' lo strato 4 (mutabile): il renderer legge ui_manifest.json e si
ridisegna; questa shell (core) non cambia mai. Il permission broker usa
un dialog JS sincrono via webview.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading

from seed import __version__

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
        self._allow_terminate = False
        self._tray_active = False   # se True, la chiusura va in background (tray)

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
            "provider_hub": self._app.ui_provider_status(),
            "operations": self._app.ui_operations(),
            "app_version": __version__,
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

    def runtime_completion_status(self) -> dict:
        return self._app.runtime_completion_status()

    # --- P0 Provider Hub ------------------------------------------------
    def provider_status(self) -> dict:
        return self._app.ui_provider_status()

    def provider_validate(self, provider: str, api_key: str,
                          roles: dict | None = None) -> dict:
        return self._app.ui_provider_validate(provider, api_key, roles)

    def provider_test(self, provider: str) -> dict:
        return self._app.ui_provider_test(provider)

    def provider_set_active(self, provider: str) -> dict:
        return self._app.ui_provider_set_active(provider)

    def provider_set_roles(self, provider: str, roles: dict) -> dict:
        return self._app.ui_provider_set_roles(provider, roles)

    def provider_restore_preset(self, provider: str) -> dict:
        return self._app.ui_provider_restore_preset(provider)

    def provider_revoke(self, provider: str) -> dict:
        return self._app.ui_provider_revoke(provider)

    def explain_last(self) -> str:
        return self._app.ui_explain_last()

    # --- Sistema: tool builder / mutazioni / operazioni / delega --------
    def tool_candidates(self) -> list:
        return self._app.ui_tool_candidates()

    def tool_install(self, capability_id: str, owner_approved: bool) -> dict:
        return self._app.ui_tool_install(capability_id, owner_approved)

    def mutation_status(self) -> dict:
        return self._app.ui_mutation_status()

    def advance_mutations(self, owner_approved_canary: bool = False) -> list:
        return self._app.ui_advance_mutations(owner_approved_canary)

    def promote_mutation(self, mutation_id: str, owner_approved: bool) -> dict:
        return self._app.ui_promote_mutation(mutation_id, owner_approved)

    def operations_status(self) -> dict:
        return self._app.ui_operations()

    def create_backup(self) -> str:
        return self._app.ui_create_backup()

    def update_check(self) -> dict:
        return self._app.ui_update_check()

    def update_status(self) -> dict:
        return self._app.ui_update_status()

    def update_start(self, owner_confirmed: bool) -> dict:
        return self._app.ui_update_start(bool(owner_confirmed))

    def restart_for_update(self) -> dict:
        if self._window is None or not getattr(sys, "frozen", False):
            return {"ok": False, "error": "riavvio update disponibile solo nell'app installata"}
        marker = self._app.operations.updates / "pending_update.json"
        runtime = Path(sys.executable).resolve()
        supervisor = runtime.parent.parent / "supervisor" / "SEEDSupervisor.exe"
        if not marker.is_file() or not supervisor.is_file():
            return {"ok": False, "error": "update pronto o supervisor non disponibile"}
        flags = 0
        for name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
            flags |= int(getattr(subprocess, name, 0))
        try:
            subprocess.Popen(
                [str(supervisor), "--boot", "--runtime", str(runtime),
                 "--wait-pid", str(os.getpid())],
                cwd=str(supervisor.parent),
                creationflags=flags,
                close_fds=True,
            )
            self._allow_terminate = True
            self._window.destroy()
            return {"ok": True}
        except OSError as exc:
            log.warning("riavvio per update fallito: %s", exc)
            return {"ok": False, "error": str(exc)}

    def delegation_status(self) -> dict:
        return self._app.ui_delegation_status()

    def set_observation_consent(self, obs_class: str, enabled: bool) -> dict:
        return self._app.ui_set_observation_consent(obs_class, enabled)

    def revoke_observations(self) -> dict:
        return self._app.ui_revoke_observations()

    # --- orb state / daemon (U0/U1) -------------------------------------
    def daemon_status(self) -> dict:
        return self._app.run_daemon_review()

    def windows_startup_status(self) -> dict:
        return self._app.startup.status()

    def set_windows_startup(self, enabled: bool, owner_approved: bool) -> dict:
        return self._app.ui_set_windows_startup(enabled, owner_approved)

    # --- P6 Adaptive Web Rendering (gated, default OFF) -----------------
    def web_render_status(self) -> dict:
        return self._app.ui_web_render_status()

    def web_render_preview(self, source_mode: str, source_ref: str,
                           provided_html: str = "",
                           accessibility_needs: list | None = None,
                           explicit_preferences: list | None = None,
                           consent: bool = False) -> dict:
        return self._app.ui_web_render_preview(
            source_mode=source_mode, source_ref=source_ref,
            provided_html=provided_html,
            accessibility_needs=tuple(accessibility_needs or ()),
            explicit_preferences=tuple(explicit_preferences or ()),
            consent=bool(consent))

    def web_render_promote(self, owner_approved: bool, persist: bool = False) -> dict:
        return self._app.ui_web_render_promote(
            owner_approved=bool(owner_approved), persist=bool(persist))

    # --- P7 Selective Capability Forge (gated, default OFF) -------------
    def forge_status(self) -> dict:
        return self._app.ui_forge_status()

    def forge_timeline(self) -> list:
        return self._app.ui_forge_timeline()

    def forge_grant_observation(self, source: str, on: bool = True) -> dict:
        return self._app.ui_forge_grant_observation(source, bool(on))

    def forge_forget_source(self, source: str) -> dict:
        return self._app.ui_forge_forget_source(source)

    def forge_suppress(self, goal: str, days: int = 30) -> dict:
        return self._app.ui_forge_suppress(goal, int(days))

    def forge_revoke_connection(self, connection_id: str) -> dict:
        return self._app.ui_forge_revoke_connection(connection_id)

    # --- voice (facoltativo, U3) -----------------------------------------
    def voice_available(self) -> bool:
        return self._app.voice.available

    # BYOK ElevenLabs: opzionale, skippabile. Solo per abilitare la voce.
    def voice_credentials_status(self) -> dict:
        return self._app.ui_voice_credentials_status()

    def voice_set_key(self, api_key: str) -> dict:
        return self._app.ui_voice_set_key(api_key)

    def voice_skip(self) -> dict:
        return self._app.ui_voice_skip()

    def voice_revoke_key(self) -> dict:
        return self._app.ui_voice_revoke()

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
    # --- controlli finestra (frameless: titlebar custom) ----------------
    def window_minimize(self) -> dict:
        if self._window is None:
            return {"ok": False}
        try:
            self._window.minimize()
            return {"ok": True}
        except Exception as exc:
            log.warning("minimize fallito: %s", exc)
            return {"ok": False, "error": str(exc)}

    def window_close(self, keep_heartbeat: bool) -> dict:
        if self._window is None:
            return {"ok": False}
        try:
            if keep_heartbeat:
                self._window.hide()
                self._app.memory.add_event("window_hidden_for_heartbeat", {})
                return {"ok": True, "action": "hidden", "heartbeat_running": True}
            self._allow_terminate = True
            self._window.destroy()
            return {"ok": True, "action": "terminated", "heartbeat_running": False}
        except Exception as exc:
            log.warning("close fallito: %s", exc)
            return {"ok": False, "error": str(exc)}

    def handle_native_closing(self) -> bool:
        """Cancel native close when the owner chooses background heartbeat."""
        if self._allow_terminate or self._window is None:
            return True
        # Con la tray attiva: chiudere = ridursi in background (niente prompt),
        # come Wispr. Si esce davvero dal menu "Esci" della tray.
        if self._tray_active:
            try:
                self._window.hide()
                self._app.memory.add_event("window_hidden_to_tray", {})
            except Exception as exc:
                log.warning("hide su chiusura fallito: %s", exc)
            return False
        try:
            keep = bool(self._window.evaluate_js(
                "confirm('Lasciare SEED attivo in background per mantenere heartbeat?\\n\\n"
                "OK: mantieni heartbeat. Annulla: termina SEED.')"))
            if keep:
                self._window.hide()
                self._app.memory.add_event("window_hidden_for_heartbeat", {})
                return False
            self._allow_terminate = True
            return True
        except Exception as exc:
            log.warning("prompt chiusura nativa fallito: %s", exc)
            return False

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

    def set_overlay_size(self, expanded: bool) -> dict:
        """Overlay command-bar: collassato (sola barra) o espanso (barra +
        risposta scrollabile), restando on_top. Niente cambio di modalita'."""
        if self._window is None:
            return {"ok": False}
        try:
            self._window.resize(660, 360 if expanded else 116)
            return {"ok": True, "expanded": bool(expanded)}
        except Exception as exc:
            log.warning("overlay resize fallito: %s", exc)
            return {"ok": False, "error": str(exc)}

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


def run_window(app, *, start_hidden: bool = False) -> None:
    import webview  # pywebview

    api = JsApi(app)
    window = webview.create_window(
        "SEED", url=str(_SURFACE / "index.html"), js_api=api,
        width=900, height=640, min_size=(360, 82),
        frameless=True, easy_drag=False,        # niente barra titolo del SO
        background_color="#f6f5f2")
    api.attach(window)
    window.events.closing += api.handle_native_closing

    def _summon(overlay: bool) -> None:
        try:
            window.show()
            window.restore()
            fn = "seedToggleOverlayFromHost" if overlay else "seedShowFull"
            window.evaluate_js(f"window.{fn} && window.{fn}()")
        except Exception as exc:
            log.warning("summon da tray fallito: %s", exc)

    def _quit_from_tray() -> None:
        api._allow_terminate = True
        try:
            window.destroy()
        except Exception as exc:
            log.warning("uscita da tray fallita: %s", exc)

    def _on_start():
        app.start_background()
        _start_overlay_hotkey(window)
        # Icona background (Wispr-like): apri pieno, cattura rapida, esci.
        from .tray import start_tray
        if start_tray(on_open=lambda: _summon(False),
                      on_quick=lambda: _summon(True),
                      on_quit=_quit_from_tray) is not None:
            api._tray_active = True
        if start_hidden:
            window.hide()
            app.memory.add_event("window_started_hidden_for_heartbeat", {})

    webview.start(_on_start, private_mode=False)
    app.shutdown()
