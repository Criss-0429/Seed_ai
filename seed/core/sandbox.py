"""Sandbox executor + audit statico AST per il codice delle capability.

Contratto di esecuzione del tool:
  - subprocess separato, CWD = workspace della capability
  - env minimale: NIENTE API key, niente variabili non necessarie
  - input: JSON su stdin; output: JSON su stdout
  - timeout hard con kill dell'albero processi
"""

from __future__ import annotations

import ast
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import forbidden
from .isolation import IsolationPolicy, run_python

log = logging.getLogger("seed.sandbox")

# ---------------------------------------------------------------------------
# AUDIT STATICO
# ---------------------------------------------------------------------------
_IMPORT_ALLOWLIST = {
    "json", "re", "math", "datetime", "pathlib", "csv", "collections",
    "itertools", "textwrap", "statistics", "html", "base64", "string",
    "unicodedata", "difflib", "random", "time", "sys", "typing", "dataclasses",
}
_NETWORK_IMPORTS = {"socket", "urllib", "requests", "httpx", "http", "ftplib",
                    "smtplib", "websocket", "websockets", "aiohttp"}
_DENY_IMPORTS = {"ctypes", "winreg", "subprocess", "multiprocessing",
                 "importlib", "pickle", "shelve", "marshal", "code",
                 "pty", "signal", "shutil"}
_DENY_CALLS = {"eval", "exec", "compile", "__import__", "globals", "locals",
               "vars", "delattr", "setattr", "input", "breakpoint"}
_DENY_OS_ATTRS = {"system", "popen", "execv", "execve", "execvp", "spawnl",
                  "spawnv", "remove", "unlink", "rmdir", "removedirs", "rename",
                  "replace", "chmod", "chown", "kill", "startfile"}


@dataclass
class AuditResult:
    passed: bool
    violations: list[str] = field(default_factory=list)


def static_audit(code: str, *, needs_network: bool = False) -> AuditResult:
    """Parsing AST + regole DENY/allowlist della doc 04. Reject = non si registra."""
    violations: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return AuditResult(False, [f"syntax error: {exc}"])

    for node in ast.walk(tree):
        # import
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) \
                else [node.module or ""]
            for name in names:
                root = name.split(".")[0]
                if root in _DENY_IMPORTS:
                    violations.append(f"import vietato: {root}")
                elif root in _NETWORK_IMPORTS and not needs_network:
                    violations.append(f"import di rete senza needs_network: {root}")
                elif root == "os":
                    pass  # os limitato sotto, via attributi
                elif root not in _IMPORT_ALLOWLIST and root not in _NETWORK_IMPORTS and root != "os":
                    violations.append(f"import fuori allowlist: {root}")
        # chiamate pericolose
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in _DENY_CALLS:
                violations.append(f"chiamata vietata: {fn.id}()")
            if isinstance(fn, ast.Attribute):
                if isinstance(fn.value, ast.Name) and fn.value.id == "os" \
                        and fn.attr in _DENY_OS_ATTRS:
                    violations.append(f"os.{fn.attr} vietato")
                if fn.attr == "__import__":
                    violations.append("__import__ dinamico vietato")
        # path vietati hardcodati nel codice
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value.lower()
            if any(tok in v for tok in (r"c:\windows", r"c:\program files",
                                        r"c:\programdata", "system32", "ntuser.dat",
                                        ".ssh", "appdata\\roaming\\microsoft")):
                violations.append(f"path vietato nel codice: {node.value[:60]}")

    return AuditResult(passed=not violations, violations=violations)


# ---------------------------------------------------------------------------
# ESECUZIONE
# ---------------------------------------------------------------------------
@dataclass
class RunResult:
    ok: bool
    output: dict = field(default_factory=dict)
    stderr: str = ""
    timed_out: bool = False


def _minimal_env() -> dict:
    """Env senza key, senza variabili utente: solo il minimo per Python."""
    keep = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
            "PATH", "LANG", "LC_ALL", "PYTHONIOENCODING")
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    env["PYTHONIOENCODING"] = "utf-8"
    env["SEED_SANDBOX"] = "1"
    return env


def _python_cmd(tool_path: Path) -> list[str]:
    """In dev: interprete corrente. Frozen (PyInstaller): l'exe in modalita' --run-tool."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run-tool", str(tool_path)]
    return [sys.executable, str(tool_path)]


def run_tool(capability_dir: Path, input_payload: dict, timeout: int = 30,
             *, backend: str = "process", network_allowed: bool = False) -> RunResult:
    tool_path = capability_dir / "tool.py"
    if not tool_path.exists():
        return RunResult(False, stderr="tool.py mancante")
    timeout = max(1, min(timeout, 120))

    workspace = forbidden.workspace_dir() / capability_dir.name
    workspace.mkdir(parents=True, exist_ok=True)

    result = run_python(
        tool_path, input_payload, workspace=workspace,
        policy=IsolationPolicy(backend=backend, timeout_seconds=timeout,
                               network_allowed=network_allowed))
    return RunResult(result.ok, result.output, result.stderr, result.timed_out)


def dry_run(capability_dir: Path, manifest: dict) -> RunResult:
    """Esegue il tool con input sintetici prima della registrazione."""
    synthetic = {k: "test" for k in (manifest.get("input_schema") or {})}
    synthetic["__dry_run__"] = True
    return run_tool(capability_dir, synthetic, timeout=15)
