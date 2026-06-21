"""Single-instance guard: la seconda istanza si riconosce e non rompe nulla."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.ui.single_instance import SingleInstance  # noqa: E402


def test_first_is_primary_second_detects_running():
    first = SingleInstance()
    assert first.primary is True
    assert first.already_running is False
    if sys.platform != "win32":
        # fuori Windows degrada: ogni istanza e' primaria, nessun guard
        second = SingleInstance()
        assert second.primary is True
        return
    # su Windows il mutex con nome e' condiviso: la seconda lo vede
    second = SingleInstance()
    assert second.already_running is True
    assert second.primary is False
    # segnalare/ascoltare non deve sollevare
    second.signal_show()
    first.start_show_listener(lambda: None)


def test_signal_and_listener_are_safe_noops_without_event():
    inst = SingleInstance()
    inst._event = None
    inst.signal_show()                 # no-op, niente eccezioni
    inst.start_show_listener(lambda: None)
