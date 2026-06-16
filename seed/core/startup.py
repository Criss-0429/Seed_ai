"""Per-user Windows startup registration for SEED.

This uses HKCU only. It never creates a Windows service and never requires
administrator privileges. Enabling it is an explicit UI action.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "SEED"


def startup_command() -> str:
    """Return the command registered for the current runtime layout."""
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        supervisor = executable.parent.parent / "supervisor" / "SEEDSupervisor.exe"
        if executable.name.lower() == "seed.exe" and supervisor.is_file():
            return subprocess.list2cmdline(
                [str(supervisor), "--boot", "--runtime", str(executable), "--background"])
        return subprocess.list2cmdline([str(executable), "--background"])
    return subprocess.list2cmdline([str(executable), "-m", "seed", "--background"])


class WindowsStartup:
    def __init__(self, *, audit=None):
        self.audit = audit or (lambda kind, payload: None)

    @property
    def supported(self) -> bool:
        return os.name == "nt"

    def status(self) -> dict:
        command = self._read()
        return {
            "supported": self.supported,
            "enabled": command is not None,
            "per_user": True,
            "windows_service": False,
            "admin_required": False,
            "consent_required": True,
        }

    def set_enabled(self, enabled: bool, *, owner_approved: bool) -> dict:
        if not self.supported:
            return {**self.status(), "ok": False, "error": "windows_only"}
        if not owner_approved:
            return {**self.status(), "ok": False, "error": "owner_approval_required"}
        import winreg

        with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        self.audit("windows_startup_changed", {"enabled": bool(enabled), "per_user": True})
        return {**self.status(), "ok": True}

    def _read(self) -> str | None:
        if not self.supported:
            return None
        import winreg

        try:
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
                value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
                return str(value)
        except FileNotFoundError:
            return None
