"""Single-instance guard (Windows).

Aprire SEED una seconda volta NON deve avviare un nuovo processo: ogni istanza
carica i modelli ML (GB di RAM) e apre lo stesso ``seed.db``; due processi in
parallelo si contendono il DB (lock, busy_timeout) e i messaggi non vengono
elaborati. Qui usiamo un mutex con nome: la seconda istanza segnala alla prima
di mostrarsi e termina subito, prima di caricare qualsiasi cosa.

Fuori da Windows degrada a no-op (si comporta sempre come istanza primaria).
"""

from __future__ import annotations

import getpass
import logging
import sys
import threading
from typing import Callable

log = logging.getLogger("seed.ui.single_instance")

_ERROR_ALREADY_EXISTS = 183
_WAIT_OBJECT_0 = 0
_INFINITE = 0xFFFFFFFF


def _names() -> tuple[str, str]:
    user = getpass.getuser() or "user"
    return f"Local\\SEED_singleton_{user}", f"Local\\SEED_show_{user}"


class SingleInstance:
    def __init__(self) -> None:
        self.primary = True
        self.already_running = False
        self._mutex = None
        self._event = None
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            k32 = ctypes.windll.kernel32
            k32.CreateMutexW.restype = wintypes.HANDLE
            k32.CreateEventW.restype = wintypes.HANDLE
            mutex_name, event_name = _names()
            self._mutex = k32.CreateMutexW(None, False, mutex_name)
            if k32.GetLastError() == _ERROR_ALREADY_EXISTS:
                self.already_running = True
                self.primary = False
            # evento "mostra l'istanza esistente" (auto-reset)
            self._event = k32.CreateEventW(None, False, False, event_name)
        except Exception as exc:  # API non disponibile: degrada a primaria
            log.warning("single-instance non disponibile (%s)", exc)
            self.primary = True
            self.already_running = False

    def signal_show(self) -> None:
        """Chiede all'istanza primaria di mostrarsi."""
        if self._event is None or sys.platform != "win32":
            return
        try:
            import ctypes
            ctypes.windll.kernel32.SetEvent(self._event)
        except Exception as exc:
            log.warning("signal_show fallito: %s", exc)

    def start_show_listener(self, on_show: Callable[[], None]) -> None:
        """Solo nell'istanza primaria: in un thread, attende il segnale e mostra."""
        if self._event is None or sys.platform != "win32":
            return

        def _loop() -> None:
            import ctypes
            k32 = ctypes.windll.kernel32
            while True:
                if k32.WaitForSingleObject(self._event, _INFINITE) == _WAIT_OBJECT_0:
                    try:
                        on_show()
                    except Exception as exc:
                        log.warning("show da seconda istanza fallito: %s", exc)

        threading.Thread(target=_loop, name="seed-singleton", daemon=True).start()
