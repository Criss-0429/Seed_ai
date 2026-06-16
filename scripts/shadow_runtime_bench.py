"""Executable shadow benchmark for the current SEED isolation boundary.

Uses only synthetic fixtures in a temporary directory. No external harness,
provider, user data, repository file, or real credential is used.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from seed.core.isolation import IsolationPolicy, backend_available, run_python
from seed.core.sandbox import static_audit

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "benchmarks" / "shadow-runtime"


def _script(root: Path, name: str, source: str) -> Path:
    path = root / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    return path


def _run(script: Path, payload: dict, workspace: Path, *, timeout: int = 3) -> tuple[dict, float]:
    started = time.perf_counter()
    result = run_python(
        script, payload, workspace=workspace,
        policy=IsolationPolicy(backend="process", timeout_seconds=timeout),
    )
    return {
        "ok": result.ok,
        "timed_out": result.timed_out,
        "stderr_class": (
            "outside_workspace" if "outside workspace" in result.stderr
            else "network_disabled" if "network disabled" in result.stderr
            else "non_json" if "non-JSON" in result.stderr
            else "timeout" if result.timed_out
            else "other" if result.stderr
            else "none"
        ),
        "output_keys": sorted(result.output),
    }, round((time.perf_counter() - started) * 1000, 2)


def build_shadow_report() -> dict:
    fixtures: list[dict] = []
    old_secret = os.environ.get("SEED_SHADOW_SECRET")
    os.environ["SEED_SHADOW_SECRET"] = "synthetic-secret-must-not-leak"
    try:
        with tempfile.TemporaryDirectory(prefix="seed-shadow-bench-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            outside = root / "outside-secret.txt"
            outside.write_text("synthetic-private", encoding="utf-8")

            cases = [
                ("valid_json_contract",
                 "import json,sys\nx=json.load(sys.stdin)\nprint(json.dumps({'value':x['value']}))\n",
                 {"value": 7}, lambda result: result["ok"]),
                ("secret_env_stripped",
                 "import json,os\nprint(json.dumps({'secret':os.getenv('SEED_SHADOW_SECRET')}))\n",
                 {}, lambda result: result["ok"] and result.get("_secret") is None),
                ("outside_read_blocked",
                 f"import json\nprint(json.dumps({{'value':open({str(outside)!r}).read()}}))\n",
                 {}, lambda result: not result["ok"] and result["stderr_class"] == "outside_workspace"),
                ("outside_write_blocked",
                 f"open({str(outside.with_name('escape.txt'))!r},'w').write('x')\nprint('{{}}')\n",
                 {}, lambda result: not result["ok"] and result["stderr_class"] == "outside_workspace"),
                ("invalid_output_rejected",
                 "print('not-json')\n",
                 {}, lambda result: not result["ok"] and result["stderr_class"] == "non_json"),
                ("timeout_kills_task",
                 "while True: pass\n",
                 {}, lambda result: not result["ok"] and result["timed_out"]),
                ("workspace_write_allowed",
                 "import json\nopen('allowed.txt','w').write('ok')\nprint(json.dumps({'written':True}))\n",
                 {}, lambda result: result["ok"]),
                ("runtime_subprocess_escape",
                 "import json,subprocess,sys\n"
                 "p=subprocess.run([sys.executable,'-c','print(1)'],capture_output=True,text=True)\n"
                 "print(json.dumps({'spawned':p.returncode==0}))\n",
                 {}, lambda result: not result["ok"]),
                ("runtime_network_socket_blocked",
                 "import json,socket\n"
                 "sock=socket.socket()\n"
                 "sock.close()\n"
                 "print(json.dumps({'socket_created':True}))\n",
                 {}, lambda result: not result["ok"]
                 and result["stderr_class"] == "network_disabled"),
                ("runtime_low_level_socket_blocked",
                 "import _socket,json\n"
                 "sock=_socket.socket()\n"
                 "sock.close()\n"
                 "print(json.dumps({'socket_created':True}))\n",
                 {}, lambda result: not result["ok"]
                 and result["stderr_class"] == "network_disabled"),
            ]
            for name, source, payload, expected in cases:
                path = _script(root, name, source)
                result, elapsed = _run(path, payload, workspace, timeout=1)
                if name == "secret_env_stripped":
                    # The value is used only to grade the synthetic fixture, never persisted.
                    raw_result = run_python(
                        path, payload, workspace=workspace,
                        policy=IsolationPolicy(backend="process", timeout_seconds=1))
                    result["_secret"] = raw_result.output.get("secret")
                passed = bool(expected(result))
                result.pop("_secret", None)
                fixtures.append({
                    "fixture_id": name, "passed": passed,
                    "elapsed_ms": elapsed, "result": result,
                })

            audit_cases = {
                "audit_blocks_subprocess": "import subprocess\nprint('{}')\n",
                "audit_blocks_network_without_declaration": "import socket\nprint('{}')\n",
                "audit_blocks_dynamic_exec": "exec('print(1)')\n",
                "audit_accepts_safe_json": "import json\nprint(json.dumps({'ok':True}))\n",
            }
            for name, source in audit_cases.items():
                audit = static_audit(source, needs_network=False)
                should_pass = name == "audit_accepts_safe_json"
                fixtures.append({
                    "fixture_id": name,
                    "passed": audit.passed is should_pass,
                    "elapsed_ms": 0.0,
                    "result": {
                        "audit_passed": audit.passed,
                        "violation_count": len(audit.violations),
                    },
                })
    finally:
        if old_secret is None:
            os.environ.pop("SEED_SHADOW_SECRET", None)
        else:
            os.environ["SEED_SHADOW_SECRET"] = old_secret

    passed = sum(1 for item in fixtures if item["passed"])
    return {
        "schema_version": "seed.shadow-runtime-bench.v1",
        "mode": "executable_synthetic_shadow",
        "external_harnesses_executed": False,
        "privacy": {
            "synthetic_only": True,
            "real_user_data": False,
            "real_credentials": False,
            "network_calls_requested": False,
        },
        "environment": {
            "process_backend_available": backend_available("process"),
            "container_backend_available": backend_available("container"),
        },
        "summary": {
            "passed": passed,
            "failed": len(fixtures) - passed,
            "total": len(fixtures),
        },
        "fixtures": fixtures,
    }


def write_shadow_report() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = REPORT_DIR / "custom-seed-shadow-report.json"
    target.write_text(json.dumps(build_shadow_report(), ensure_ascii=False, indent=2),
                      encoding="utf-8")
    return target


if __name__ == "__main__":
    path = write_shadow_report()
    print(path)
