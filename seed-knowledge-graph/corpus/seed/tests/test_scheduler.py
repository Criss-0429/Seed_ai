"""Scheduler compatibility tests for proposal-only reflection."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.scheduler import Scheduler  # noqa: E402


class _Watcher:
    def is_user_idle(self):
        return True

    def start(self):
        pass

    def stop(self):
        pass


class _Evolution:
    def __init__(self):
        self.calls = 0

    def already_ran_today(self):
        return False

    def run_reflection(self):
        self.calls += 1
        return {"applied": [], "proposed": [{"mutation_id": "m1"}], "notes": []}


def test_scheduler_notifies_proposal_only_digest():
    received = []
    scheduler = Scheduler(_Watcher(), _Evolution(), on_digest=received.append)
    scheduler._maybe_reflect()
    assert received and received[0]["proposed"][0]["mutation_id"] == "m1"


def test_scheduler_blocks_automatic_and_forced_reflection_during_onboarding():
    evolution = _Evolution()
    scheduler = Scheduler(_Watcher(), evolution, can_reflect=lambda: False)

    scheduler._maybe_reflect()
    digest = scheduler.force_reflection()

    assert evolution.calls == 0
    assert digest["proposed"] == []
    assert "onboarding" in digest["notes"][0].lower()


def test_report_barrier_waits_for_running_reflection():
    entered = threading.Event()
    release = threading.Event()

    class SlowEvolution(_Evolution):
        def run_reflection(self):
            entered.set()
            release.wait(timeout=2)
            return super().run_reflection()

    scheduler = Scheduler(_Watcher(), SlowEvolution())
    worker = threading.Thread(target=scheduler.force_reflection)
    worker.start()
    assert entered.wait(timeout=1)

    barrier_done = threading.Event()
    waiter = threading.Thread(
        target=lambda: (scheduler.wait_for_reflection(), barrier_done.set()))
    waiter.start()
    time.sleep(0.05)
    assert not barrier_done.is_set()

    release.set()
    worker.join(timeout=2)
    waiter.join(timeout=2)
    assert barrier_done.is_set()
