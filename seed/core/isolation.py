"""Real isolated execution backends used by workers, delegates and tool forge."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class IsolationPolicy:
    backend: str = "process"  # process | container
    timeout_seconds: int = 30
    memory_mb: int = 256
    cpu_count: float = 1.0
    pids_limit: int = 64
    network_allowed: bool = False
    container_image: str = "python:3.12-alpine"

    def validate(self) -> None:
        if self.backend not in {"process", "container"}:
            raise ValueError(f"unsupported isolation backend: {self.backend}")
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("timeout_seconds outside [1,300]")
        if self.memory_mb < 64 or self.pids_limit < 8 or self.cpu_count <= 0:
            raise ValueError("invalid isolation resource limits")


@dataclass(frozen=True)
class IsolationResult:
    ok: bool
    output: dict = field(default_factory=dict)
    stderr: str = ""
    timed_out: bool = False
    backend: str = ""
    command: tuple[str, ...] = ()


def backend_available(backend: str) -> bool:
    if backend == "process":
        return True
    if backend != "container" or not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run_python(
    script: Path,
    payload: dict,
    *,
    workspace: Path,
    policy: IsolationPolicy,
) -> IsolationResult:
    """Execute a Python JSON stdin/stdout contract, never through a shell."""
    policy.validate()
    script = Path(script).resolve()
    workspace = Path(workspace).resolve()
    if not script.is_file():
        return IsolationResult(False, stderr="script missing", backend=policy.backend)
    workspace.mkdir(parents=True, exist_ok=True)
    if policy.backend == "container":
        return _run_container(script, payload, workspace, policy)
    return _run_process(script, payload, workspace, policy)


def _minimal_env() -> dict[str, str]:
    keep = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "PATH"}
    env = {key: value for key, value in os.environ.items() if key.upper() in keep}
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
                "SEED_ISOLATED": "1"})
    return env


def _run_process(
    script: Path, payload: dict, workspace: Path, policy: IsolationPolicy,
) -> IsolationResult:
    if getattr(sys, "frozen", False):
        command = (sys.executable, "--run-isolated-tool", str(script))
    else:
        runner = Path(__file__).with_name("process_runner.py").resolve()
        command = (sys.executable, "-I", "-B", str(runner), str(script))
    try:
        proc = subprocess.run(
            command, input=json.dumps(payload, ensure_ascii=False),
            capture_output=True, text=True, encoding="utf-8", cwd=workspace,
            env=_minimal_env(), timeout=policy.timeout_seconds,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        return IsolationResult(False, stderr="timeout", timed_out=True,
                               backend="process", command=command)
    except OSError as exc:
        return IsolationResult(False, stderr=str(exc), backend="process", command=command)
    return _decode(proc.returncode, proc.stdout, proc.stderr, "process", command)


def _run_container(
    script: Path, payload: dict, workspace: Path, policy: IsolationPolicy,
) -> IsolationResult:
    if not backend_available("container"):
        return IsolationResult(False, stderr="container backend unavailable",
                               backend="container")
    script_mount = f"{script.parent}:/seed-tool:ro"
    workspace_mount = f"{workspace}:/workspace:rw"
    command = [
        "docker", "run", "--rm", "--init", "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        f"--memory={policy.memory_mb}m", f"--cpus={policy.cpu_count}",
        f"--pids-limit={policy.pids_limit}", "--tmpfs=/tmp:rw,noexec,nosuid,size=32m",
        "--workdir=/workspace", "-i",
        "-v", script_mount, "-v", workspace_mount,
    ]
    command += ["--network=bridge"] if policy.network_allowed else ["--network=none"]
    command += [policy.container_image, "python", "-I", "-B", f"/seed-tool/{script.name}"]
    try:
        proc = subprocess.run(
            command, input=json.dumps(payload, ensure_ascii=False),
            capture_output=True, text=True, encoding="utf-8",
            timeout=policy.timeout_seconds,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        return IsolationResult(False, stderr="timeout", timed_out=True,
                               backend="container", command=tuple(command))
    except OSError as exc:
        return IsolationResult(False, stderr=str(exc), backend="container",
                               command=tuple(command))
    return _decode(proc.returncode, proc.stdout, proc.stderr, "container", tuple(command))


def _decode(returncode: int, stdout: str, stderr: str, backend: str,
            command: tuple[str, ...] | list[str]) -> IsolationResult:
    if returncode != 0:
        return IsolationResult(False, stderr=stderr[-2000:] or f"exit {returncode}",
                               backend=backend, command=tuple(command))
    try:
        output = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return IsolationResult(False, stderr=f"non-JSON output: {stdout[:200]}",
                               backend=backend, command=tuple(command))
    if not isinstance(output, dict):
        return IsolationResult(False, stderr="output must be a JSON object",
                               backend=backend, command=tuple(command))
    return IsolationResult(True, output=output, stderr=stderr[-2000:],
                           backend=backend, command=tuple(command))
