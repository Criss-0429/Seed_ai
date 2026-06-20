"""Tray background (Wispr-like): degrada senza pystray, callback robusti."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.ui import tray  # noqa: E402


def _noop():
    pass


def test_start_tray_degrades_without_pystray(monkeypatch):
    # forza l'assenza di pystray -> deve ritornare None, niente eccezioni
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "pystray":
            raise ImportError("no pystray")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = tray.start_tray(on_open=_noop, on_quick=_noop, on_quit=_noop)
    assert result is None


def test_start_tray_returns_none_or_icon_without_crash():
    # ambiente test senza display: non deve mai sollevare
    result = tray.start_tray(on_open=_noop, on_quick=_noop, on_quit=_noop)
    assert result is None or hasattr(result, "stop")
