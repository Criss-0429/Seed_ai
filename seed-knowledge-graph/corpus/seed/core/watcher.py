"""Activity watcher: processi + finestra attiva + media. Niente screenshot,
niente keylogging, niente contenuti (doc 05).

I titoli finestra passano dal privacy gate PRIMA di toccare il disco.
Su sistemi non-Windows il watcher e' un no-op (dev mode).
"""

from __future__ import annotations

import logging
import os
import threading
import time

log = logging.getLogger("seed.watcher")

# categorie locali: exe -> categoria (estendibile dall'evoluzione via policy,
# NON da questo modulo che e' core)
_APP_CATEGORIES = {
    "steam.exe": "gaming", "epicgameslauncher.exe": "gaming",
    "excel.exe": "office", "winword.exe": "office", "powerpnt.exe": "office",
    "outlook.exe": "comunicazione", "thunderbird.exe": "comunicazione",
    "acad.exe": "creatività", "photoshop.exe": "creatività", "blender.exe": "creatività",
    "code.exe": "dev", "pycharm64.exe": "dev", "devenv.exe": "dev",
    "chrome.exe": "browser", "msedge.exe": "browser", "firefox.exe": "browser",
    "spotify.exe": "media", "vlc.exe": "media",
    "discord.exe": "comunicazione", "telegram.exe": "comunicazione",
    "whatsapp.exe": "comunicazione",
}
_MEDIA_APPS = {"spotify.exe", "vlc.exe", "wmplayer.exe", "musicbee.exe"}


def _foreground_window() -> tuple[str, str]:
    """(exe_name, window_title) della finestra in foreground. Windows only."""
    if os.name != "nt":
        return "", ""
    try:
        import ctypes
        import ctypes.wintypes as wt
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "", ""
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = ""
        try:
            import psutil
            exe = psutil.Process(pid.value).name().lower()
        except Exception:
            pass
        return exe, buf.value
    except Exception as exc:
        log.debug("foreground fail: %s", exc)
        return "", ""


def _is_idle(threshold_s: int = 300) -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0 > threshold_s
    except Exception:
        return False


class ActivityWatcher:
    def __init__(self, memory, privacy_gate, poll_seconds: int = 5,
                 excluded_apps: list[str] | None = None):
        self._memory = memory
        self._gate = privacy_gate
        self._poll = poll_seconds
        self._excluded = {a.lower() for a in (excluded_apps or [])}
        self._stop = threading.Event()
        self._paused_until: float = 0.0
        self._onboarding_blocked = False
        self._session: dict | None = None  # sessione d'uso corrente
        self._thread: threading.Thread | None = None

    # -- controlli utente -------------------------------------------------
    def pause(self, minutes: int = 60) -> None:
        self._paused_until = time.time() + minutes * 60 if minutes > 0 else float("inf")
        self._flush_session()
        self._memory.add_event("watcher_paused", {"minutes": minutes})

    def resume(self) -> None:
        self._paused_until = 0.0
        self._memory.add_event("watcher_resumed", {})

    def set_onboarding_blocked(self, blocked: bool) -> None:
        """Blocco interno: nessuna osservazione prima della fine onboarding."""
        self._onboarding_blocked = bool(blocked)
        if blocked:
            self._flush_session()

    @property
    def paused(self) -> bool:
        return self._onboarding_blocked or time.time() < self._paused_until

    def is_user_idle(self) -> bool:
        return _is_idle()

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        if os.name != "nt":
            log.info("watcher: no-op su questo OS (dev mode)")
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="seed-watcher")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._flush_session()

    # -- loop -----------------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop.wait(self._poll):
            if self.paused:
                continue
            exe, title = _foreground_window()
            if not exe or exe in self._excluded:
                continue
            now = time.time()
            if self._session and self._session["app"] == exe:
                self._session["end"] = now
                self._session["last_title"] = title
            else:
                self._flush_session()
                self._session = {"app": exe, "first_title": title,
                                 "last_title": title, "start": now, "end": now}

    def _flush_session(self) -> None:
        s, self._session = self._session, None
        if not s or (s["end"] - s["start"]) < 10:  # sessioni <10s: rumore
            return
        category = _APP_CATEGORIES.get(s["app"], "altro")
        media = s["app"] in _MEDIA_APPS
        # REDAZIONE PRIMA DEL DISCO: i titoli contengono nomi file/persone
        ft = self._gate.redact(s["first_title"], purpose="storage").text
        lt = self._gate.redact(s["last_title"], purpose="storage").text
        self._memory.add_episode("watcher", {
            "app": s["app"], "category": category, "media": media,
            "title_first": ft, "title_last": lt,
            "start": s["start"], "end": s["end"],
            "duration_s": round(s["end"] - s["start"]),
        }, category=category)
