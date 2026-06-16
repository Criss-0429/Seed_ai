"""Path Windows vietati — HARDCODED nel core, non configurabili a runtime.

Questo modulo e' parte del core immutabile: l'evolution engine non puo'
modificarlo, le capability non possono aggirarlo (il sandbox executor valida
ogni path attraverso queste funzioni prima di qualunque I/O).

Modalita':
  - "write"   : scrittura/creazione/modifica/cancellazione
  - "execute" : esecuzione di binari
  - "read"    : lettura
Default deny per write fuori dalle cartelle consentite.
"""

from __future__ import annotations

import fnmatch
import getpass
import os
from pathlib import Path

# --------------------------------------------------------------------------
# Radici di sistema: scrittura ed esecuzione SEMPRE vietate
# --------------------------------------------------------------------------
_SYSTEM_ROOTS = [
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData",
    r"C:\$Recycle.Bin",
    r"C:\System Volume Information",
    r"C:\Recovery",
    r"C:\Boot",
    r"C:\EFI",
    r"C:\PerfLogs",
]

# Sottoalberi del profilo utente vietati in scrittura (credenziali e simili)
_USER_SUBTREES_NO_WRITE = [
    r"AppData\Roaming\Microsoft",
    r"AppData\Local\Microsoft",
]

# Pattern di file la cui LETTURA e' sempre vietata (segreti / hive registro)
_READ_DENY_PATTERNS = [
    "*\\sam", "*\\system", "*\\security", "*\\ntuser.dat",
    "*\\.ssh\\*", "*\\.gnupg\\*",
    "*.pfx", "*.pem", "*.key", "*.p12",
    "*\\credentials\\*", "*\\vault\\*",
    "*\\.env", "*\\.env.*", "*secret*", "*token*",
    "*\\login data", "*\\login data-journal",   # password browser chromium
    "*\\cookies", "*\\cookies-journal",
    "*\\key3.db", "*\\key4.db", "*\\logins.json",  # firefox
]


def _norm(path: str | Path) -> str:
    return os.path.normpath(str(path)).lower()


def _expand_user_root() -> str:
    return _norm(Path.home())


def seed_data_dir() -> Path:
    """Radice dati SEED, con override esplicito per il boot supervisor."""
    override = os.environ.get("SEED_DATA_ROOT")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(base) / "SEED"
    return Path.home() / ".seed"


def core_config_dir() -> Path:
    """Cartella config con API key: il forge/le capability NON possono toccarla."""
    return seed_data_dir() / "core_config"


def workspace_dir() -> Path:
    """Unica cartella in cui la scrittura e' consentita di default."""
    return seed_data_dir() / "workspace"


def _is_under(path: str, root: str) -> bool:
    path, root = _norm(path), _norm(root)
    return path == root or path.startswith(root + os.sep)


def _is_other_user_profile(path: str) -> bool:
    """True se il path e' dentro C:\\Users\\<qualcun altro>."""
    p = _norm(path)
    users_root = _norm(r"C:\Users") + os.sep
    if not p.startswith(users_root):
        return False
    me = getpass.getuser().lower()
    rest = p[len(users_root):]
    profile = rest.split(os.sep, 1)[0]
    return profile not in (me, "public")  # Public: lettura ok, scrittura negata sotto


def is_read_denied(path: str | Path) -> bool:
    p = _norm(path)
    if _is_other_user_profile(p):
        return True
    for pattern in _READ_DENY_PATTERNS:
        if fnmatch.fnmatch(p, _norm(pattern)) or fnmatch.fnmatch(os.path.basename(p), pattern.split("\\")[-1]):
            return True
    # hive del registro ovunque si trovino
    base = os.path.basename(p)
    if base in ("sam", "system", "security", "software", "ntuser.dat"):
        if "windows" in p or "config" in p or base == "ntuser.dat":
            return True
    return False


def is_write_denied(path: str | Path, allowed_extra: list[str] | None = None) -> bool:
    """Default deny: scrivibile SOLO workspace + cartelle concesse dall'utente."""
    p = _norm(path)
    # vietate sempre, anche se l'utente le "concedesse"
    for root in _SYSTEM_ROOTS:
        if _is_under(p, root):
            return True
    if _is_other_user_profile(p):
        return True
    if _is_under(p, str(Path(r"C:\Users\Public"))) or _is_under(p, str(Path(r"C:\Users\Default"))):
        return True
    home = _expand_user_root()
    for sub in _USER_SUBTREES_NO_WRITE:
        if _is_under(p, os.path.join(home, _norm(sub))):
            return True
    if _is_under(p, str(core_config_dir())):
        return True
    # allowlist
    allowed = [str(workspace_dir())] + list(allowed_extra or [])
    return not any(_is_under(p, a) for a in allowed)


def is_execute_denied(path: str | Path) -> bool:
    p = _norm(path)
    if _is_other_user_profile(p):
        return True
    # eseguire binari DENTRO le radici di sistema e' permesso solo via
    # capability open_app con allowlist (gestita dal permission broker);
    # qui vietiamo l'esecuzione di qualunque cosa scritta dal forge fuori sandbox
    # e l'esecuzione diretta in cartelle sensibili utente.
    home = _expand_user_root()
    for sub in _USER_SUBTREES_NO_WRITE:
        if _is_under(p, os.path.join(home, _norm(sub))):
            return True
    return False


def check(path: str | Path, mode: str, allowed_extra: list[str] | None = None) -> None:
    """Solleva PermissionError se il path e' vietato per la modalita' richiesta."""
    if mode == "read" and is_read_denied(path):
        raise PermissionError(f"Lettura vietata dal core: {path}")
    if mode == "write" and is_write_denied(path, allowed_extra):
        raise PermissionError(f"Scrittura vietata dal core: {path}")
    if mode == "execute" and is_execute_denied(path):
        raise PermissionError(f"Esecuzione vietata dal core: {path}")
