"""D1 daemon: in-process, heartbeat reviewable, coda proattivita' persistente,
cooldown/suppression/silenzio di default, audit aggregato, ZERO azioni."""

from __future__ import annotations

import inspect
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core import daemon as daemon_mod  # noqa: E402
from seed.core.daemon import (  # noqa: E402
    BackgroundDaemon, DaemonError, ProactivityCandidate, build_heartbeat,
    decide_proactivity, governed_net_value, HeartbeatStats,
)
from seed.core.app import SeedApp  # noqa: E402
from seed.core.memory import Memory  # noqa: E402


def _candidate(**overrides) -> ProactivityCandidate:
    base = dict(
        candidate_id="c1", category="suggestion", topic_ref="knowledge:12",
        expected_value=0.9, interruption_cost=0.1, privacy_cost=0.1,
        trust_cost=0.1, created_at=1000.0, expiry=None,
    )
    base.update(overrides)
    return ProactivityCandidate(**base)


# --- formula + validazione ------------------------------------------------
def test_governed_net_value_is_expected_minus_costs():
    cand = _candidate(expected_value=0.9, interruption_cost=0.2,
                      privacy_cost=0.1, trust_cost=0.1)
    assert governed_net_value(cand) == pytest.approx(0.5)


def test_validate_rejects_raw_text_topic_ref():
    with pytest.raises(DaemonError):
        _candidate(topic_ref="il mio progetto segreto").validate()


def test_validate_rejects_unknown_category_and_out_of_range_cost():
    with pytest.raises(DaemonError):
        _candidate(category="diagnosis").validate()
    with pytest.raises(DaemonError):
        _candidate(privacy_cost=1.5).validate()


# --- decisione deterministica --------------------------------------------
def test_emit_when_value_exceeds_cost():
    decision = decide_proactivity(_candidate(), now=2000.0)
    assert decision.action == "emit"
    assert decision.reasons == ("net_value_exceeds_cost",)


def test_default_silence_when_value_not_above_cost():
    cand = _candidate(expected_value=0.2, interruption_cost=0.2,
                      privacy_cost=0.05, trust_cost=0.05)
    decision = decide_proactivity(cand, now=2000.0)
    assert decision.action == "silence"
    assert decision.reasons == ("default_silence",)


def test_privacy_hard_gate_blocks_even_high_value():
    cand = _candidate(expected_value=0.99, privacy_cost=0.6)
    decision = decide_proactivity(cand, now=2000.0)
    assert decision.action == "suppress"
    assert decision.reasons == ("privacy_cost_high",)
    assert decision.transient is False


def test_cooldown_suppresses_transiently():
    decision = decide_proactivity(_candidate(), now=2000.0,
                                  last_emit_at=1999.0, cooldown_seconds=1800.0)
    assert decision.action == "suppress"
    assert decision.reasons == ("cooldown_active",)
    assert decision.transient is True


def test_category_suppression_is_transient():
    decision = decide_proactivity(_candidate(category="reminder"), now=2000.0,
                                  suppressed_categories=("reminder",))
    assert decision.action == "suppress"
    assert decision.transient is True


def test_expiry_is_terminal():
    decision = decide_proactivity(_candidate(expiry=1500.0), now=2000.0)
    assert decision.action == "expire"


def test_low_value_is_silenced_even_inside_cooldown():
    # Verdetto intrinseco (non saliente) batte il cooldown transiente:
    # una candidate sotto soglia non deve restare in coda dietro un cooldown.
    cand = _candidate(expected_value=0.2, interruption_cost=0.2,
                      privacy_cost=0.05, trust_cost=0.05)
    decision = decide_proactivity(cand, now=2000.0, last_emit_at=1999.0,
                                  cooldown_seconds=1800.0)
    assert decision.action == "silence"
    assert decision.transient is False


# --- heartbeat aggregato --------------------------------------------------
def test_heartbeat_is_aggregate_and_declares_boundaries():
    stats = HeartbeatStats(queue_depth=3, emitted=1, silenced=2)
    hb = build_heartbeat(tick=5, now=2000.0, stats=stats)
    assert hb["write_actions"] == 0
    assert hb["os_service"] is False
    assert hb["auto_start"] is False
    assert hb["always_on"] is False
    assert hb["supervised_process_only"] is True
    assert hb["decisions"] == {"emitted": 1, "suppressed": 0,
                               "silenced": 2, "expired": 0}
    # nessun riferimento opaco o testo nel battito
    assert "topic_ref" not in json.dumps(hb)


# --- persistenza coda -----------------------------------------------------
def test_queue_persists_and_holds_no_raw_text(tmp_path):
    mem = Memory(tmp_path / "d.db")
    daemon = BackgroundDaemon(mem, clock=lambda: 1000.0)
    daemon.enqueue(_candidate())
    items = mem.proactivity_queue_items(status="queued")
    assert len(items) == 1
    assert items[0]["topic_ref"] == "knowledge:12"
    # la coda non contiene frasi: solo categoria + ref opaco + numeri
    blob = json.dumps(items[0])
    assert "progetto" not in blob and " " not in items[0]["topic_ref"]
    mem.close()


def test_enqueue_rejects_raw_text(tmp_path):
    mem = Memory(tmp_path / "d.db")
    daemon = BackgroundDaemon(mem, clock=lambda: 1000.0)
    with pytest.raises(DaemonError):
        daemon.enqueue(_candidate(topic_ref="testo personale grezzo"))
    mem.close()


# --- tick deterministico --------------------------------------------------
class _Clock:
    def __init__(self, t=2000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_tick_emits_then_cooldown_defers_until_window_passes(tmp_path):
    mem = Memory(tmp_path / "d.db")
    clock = _Clock(2000.0)
    daemon = BackgroundDaemon(mem, clock=clock, cooldown_seconds=1800.0)
    daemon.enqueue(_candidate(candidate_id="a"))
    daemon.enqueue(_candidate(candidate_id="b"))

    daemon._tick()
    by_cid = {r["candidate_id"]: r for r in mem.proactivity_queue_items()}
    # primo emesso; il secondo nello stesso tick cade nel cooldown -> resta queued
    statuses = sorted(r["status"] for r in by_cid.values())
    assert statuses == ["emitted", "queued"]
    assert mem.daemon_state()["last_emit_at"] == 2000.0

    # avanza oltre il cooldown: il secondo viene emesso
    clock.t = 2000.0 + 1801.0
    daemon._tick()
    assert all(r["status"] == "emitted" for r in mem.proactivity_queue_items())
    mem.close()


def test_can_run_false_beats_heartbeat_but_leaves_queue_untouched(tmp_path):
    mem = Memory(tmp_path / "d.db")
    events = []
    daemon = BackgroundDaemon(
        mem, clock=_Clock(2000.0),
        audit=lambda k, p: events.append((k, p)),
        can_run=lambda: False)
    daemon.enqueue(_candidate())
    daemon._tick()
    assert mem.proactivity_queue_items(status="queued")  # intatta
    heartbeats = [p for k, p in events if k == "daemon_heartbeat"]
    assert heartbeats and heartbeats[-1]["can_run"] is False
    assert heartbeats[-1]["decisions"] == {"emitted": 0, "suppressed": 0,
                                           "silenced": 0, "expired": 0}
    assert mem.daemon_state()["tick_count"] == 1
    mem.close()


def test_audit_is_aggregate_only_no_topic_ref(tmp_path):
    mem = Memory(tmp_path / "d.db")
    events = []
    daemon = BackgroundDaemon(mem, clock=_Clock(2000.0),
                              audit=lambda k, p: events.append((k, p)))
    daemon.enqueue(_candidate(topic_ref="knowledge:99"))
    daemon._tick()
    blob = json.dumps(events)
    assert "knowledge:99" not in blob       # il ref opaco non finisce nell'audit
    assert any(k == "daemon_heartbeat" for k, _ in events)
    mem.close()


# --- confini D1 (per costruzione) -----------------------------------------
def test_daemon_has_no_execution_surface(tmp_path):
    mem = Memory(tmp_path / "d.db")
    daemon = BackgroundDaemon(mem, clock=_Clock())
    for surface in ("registry", "broker", "sandbox", "capabilities"):
        assert not hasattr(daemon, surface)
    mem.close()


def test_daemon_module_imports_no_execution_primitives():
    src = inspect.getsource(daemon_mod)
    assert "subprocess" not in src
    assert "import os" not in src
    assert "capabilities" not in src


# --- lifecycle thread -----------------------------------------------------
def test_start_stop_runs_in_process_thread(tmp_path):
    mem = Memory(tmp_path / "d.db")
    events = []
    daemon = BackgroundDaemon(mem, heartbeat_seconds=1.0,
                              audit=lambda k, p: events.append((k, p)))
    daemon.start()
    assert daemon.running
    deadline = time.time() + 2
    while time.time() < deadline and not any(
            k == "daemon_heartbeat" for k, _ in events):
        time.sleep(0.02)
    daemon.stop()
    assert not daemon.running
    assert any(k == "daemon_started" for k, _ in events)
    assert any(k == "daemon_heartbeat" for k, _ in events)
    assert any(k == "daemon_stopped" for k, _ in events)
    mem.close()


def test_disabled_daemon_does_not_start(tmp_path):
    mem = Memory(tmp_path / "d.db")
    events = []
    daemon = BackgroundDaemon(mem, enabled=False,
                              audit=lambda k, p: events.append((k, p)))
    daemon.start()
    assert not daemon.running
    assert any(k == "daemon_disabled" for k, _ in events)
    mem.close()


# --- review snapshot + comando :daemon ------------------------------------
def test_review_snapshot_is_aggregate(tmp_path):
    mem = Memory(tmp_path / "d.db")
    daemon = BackgroundDaemon(mem, clock=_Clock())
    daemon.enqueue(_candidate())
    review = daemon.review()
    assert review["write_actions"] == 0
    assert review["os_service"] is False
    assert review["supervised_process_only"] is True
    assert review["queue_status_counts"].get("queued") == 1
    assert "topic_ref" not in json.dumps(review)
    mem.close()


def test_daemon_command_is_local_and_returns_review():
    class LocalOnly:
        @staticmethod
        def run_daemon_review():
            return {"write_actions": 0, "os_service": False}

    result = json.loads(SeedApp.handle_message(LocalOnly(), ":daemon"))
    assert result["write_actions"] == 0
    assert result["os_service"] is False
