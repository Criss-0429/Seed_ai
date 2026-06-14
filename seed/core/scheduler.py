"""Job in background: watcher, reflection notturno su idle, promemoria survey.

Il reflection parte quando: (a) non e' ancora girato oggi E
(b) il PC e' idle da >5 min oppure e' l'orario notturno (>= 02:00),
oppure (c) primo avvio del giorno se il PC era spento di notte.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

log = logging.getLogger("seed.scheduler")


class Scheduler:
    def __init__(self, watcher, evolution, on_digest=None, can_reflect=None,
                 on_consolidate=None, on_lifecycle=None):
        self._watcher = watcher
        self._evolution = evolution
        self._on_digest = on_digest  # callback UI: mostra il changelog del mattino
        self._can_reflect = can_reflect or (lambda: True)
        # M2: consolidamento memoria sleep-time (estrazione knowledge candidate)
        self._on_consolidate = on_consolidate
        self._on_lifecycle = on_lifecycle
        self._stop = threading.Event()
        self._reflection_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._watcher.start()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="seed-scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._watcher.stop()

    def _loop(self) -> None:
        # check ogni 5 minuti
        while not self._stop.wait(300):
            try:
                self._maybe_reflect()
            except Exception:
                log.exception("scheduler tick fallito")

    def _maybe_reflect(self) -> None:
        with self._reflection_lock:
            self._maybe_reflect_locked()

    def _maybe_reflect_locked(self) -> None:
        if not self._can_reflect():
            log.info("reflection sospesa: onboarding non concluso")
            return
        if self._evolution.already_ran_today():
            return
        hour = datetime.now().hour
        night = 2 <= hour < 7
        idle = self._watcher.is_user_idle()
        if night or idle:
            log.info("reflection pass (night=%s idle=%s)", night, idle)
            self._consolidate()
            digest = self._evolution.run_reflection()
            self._advance_lifecycle()
            if self._on_digest and (digest.get("applied") or digest.get("proposed")):
                self._on_digest(digest)

    def _consolidate(self) -> None:
        if self._on_consolidate is None:
            return
        try:
            n = self._on_consolidate()
            if n:
                log.info("consolidamento memoria: %d claim registrati", n)
        except Exception:
            log.exception("consolidamento memoria fallito")

    def _advance_lifecycle(self) -> None:
        if self._on_lifecycle is None:
            return
        try:
            self._on_lifecycle()
        except Exception:
            log.exception("mutation lifecycle automation fallita")

    def force_reflection(self) -> dict:
        """Per il debug di Cristian e per il pilot: bottone nascosto in UI."""
        with self._reflection_lock:
            if not self._can_reflect():
                return {
                    "applied": [],
                    "proposed": [],
                    "notes": ["Reflection sospesa finche' onboarding non e' concluso."],
                }
            self._consolidate()
            digest = self._evolution.run_reflection()
            self._advance_lifecycle()
            return digest

    def wait_for_reflection(self) -> None:
        """Barrier per export/report: ritorna solo a reflection conclusa."""
        with self._reflection_lock:
            return
