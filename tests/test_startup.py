"""Windows startup is per-user, explicit, and reversible."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import startup  # noqa: E402
from seed.ui.shell import JsApi  # noqa: E402


class Key:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 1
    KEY_QUERY_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}

    def CreateKeyEx(self, *_args):
        return Key()

    def OpenKey(self, *_args):
        if startup.VALUE_NAME not in self.values:
            raise FileNotFoundError
        return Key()

    def SetValueEx(self, _key, name, _reserved, _kind, value):
        self.values[name] = value

    def QueryValueEx(self, _key, name):
        return self.values[name], self.REG_SZ

    def DeleteValue(self, _key, name):
        if name not in self.values:
            raise FileNotFoundError
        del self.values[name]


def test_windows_startup_requires_owner_and_is_reversible(monkeypatch):
    fake = FakeWinreg()
    monkeypatch.setattr(startup.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "winreg", fake)
    manager = startup.WindowsStartup()

    denied = manager.set_enabled(True, owner_approved=False)
    assert denied["error"] == "owner_approval_required"
    assert not denied["enabled"]

    enabled = manager.set_enabled(True, owner_approved=True)
    assert enabled["ok"] and enabled["enabled"]
    assert enabled["per_user"] and not enabled["windows_service"]
    assert "--background" in fake.values[startup.VALUE_NAME]

    disabled = manager.set_enabled(False, owner_approved=True)
    assert disabled["ok"] and not disabled["enabled"]


class Memory:
    def __init__(self):
        self.events = []

    def add_event(self, kind, payload):
        self.events.append((kind, payload))


class App:
    def __init__(self):
        self.memory = Memory()


class Window:
    def __init__(self, confirm=True):
        self.confirm = confirm
        self.hidden = False
        self.destroyed = False

    def hide(self):
        self.hidden = True

    def destroy(self):
        self.destroyed = True

    def evaluate_js(self, _script):
        return self.confirm


def test_close_choice_hides_or_terminates_process():
    api = JsApi(App())
    hidden = Window()
    api._window = hidden
    result = api.window_close(True)
    assert result["action"] == "hidden" and hidden.hidden and not hidden.destroyed

    terminated = Window()
    api._window = terminated
    result = api.window_close(False)
    assert result["action"] == "terminated" and terminated.destroyed


def test_native_close_can_be_cancelled_to_keep_heartbeat():
    api = JsApi(App())
    window = Window(confirm=True)
    api._window = window
    assert api.handle_native_closing() is False
    assert window.hidden and not window.destroyed
