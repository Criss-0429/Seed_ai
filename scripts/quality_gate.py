"""P2 quality gate: static checks, dependency audit, tests, and acceptance."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAT_SCOPE = [
    "scripts/build_release.py",
    "scripts/quality_gate.py",
    "scripts/size_report.py",
    "seed/core/emotion.py",
    "seed/core/model_bundle.py",
    "seed/core/provider_hub.py",
    "seed/supervisor.py",
]
SCAN_ROOTS = ["seed", "scripts", "config", "installer"]
SECRET_PATTERN = re.compile(
    r"""(?ix)
    (?:sk-[a-z0-9_-]{20,}|gh[pousr]_[a-z0-9]{20,})|
    (?:(?:api[_-]?key|token|secret)\s*[:=]\s*["'][^"'\s]{20,}["'])
    """
)


def run(label: str, command: list[str]) -> None:
    print(f"[P2] {label}")
    subprocess.run(command, cwd=ROOT, check=True)


def secret_scan() -> None:
    findings: list[str] = []
    for relative in SCAN_ROOTS:
        for path in (ROOT / relative).rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".json", ".iss", ".md"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line_number, line in enumerate(text.splitlines(), 1):
                low = line.lower()
                if SECRET_PATTERN.search(line) and not any(
                    marker in low for marker in ("dummy", "example", "redacted", "placeholder")
                ):
                    findings.append(f"{path.relative_to(ROOT)}:{line_number}")
    if findings:
        raise RuntimeError(f"secret scan findings: {', '.join(findings)}")


def import_cycle_scan() -> None:
    package = ROOT / "seed" / "core"
    graph: dict[str, set[str]] = {}
    for path in package.glob("*.py"):
        module = path.stem
        graph[module] = set()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level != 1:
                continue
            if node.module:
                graph[module].add(node.module.split(".", 1)[0])
            else:
                graph[module].update(alias.name.split(".", 1)[0] for alias in node.names)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module: str, trail: list[str]) -> None:
        if module in visiting:
            cycle = trail[trail.index(module) :] + [module]
            raise RuntimeError(f"core import cycle: {' -> '.join(cycle)}")
        if module in visited:
            return
        visiting.add(module)
        for dependency in sorted(graph.get(module, ())):
            if dependency in graph:
                visit(dependency, trail + [dependency])
        visiting.remove(module)
        visited.add(module)

    for module in sorted(graph):
        visit(module, [module])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Include tests and core acceptance.")
    args = parser.parse_args(argv)
    python = sys.executable

    run("ruff check", [python, "-m", "ruff", "check", "seed", "scripts"])
    run(
        "ruff format check (progressive P2 scope)",
        [python, "-m", "ruff", "format", "--check", *FORMAT_SCOPE],
    )
    run(
        "mypy progressive core",
        [
            python,
            "-m",
            "mypy",
            "seed/core/model_bundle.py",
            "seed/core/provider_hub.py",
            "seed/supervisor.py",
            "scripts/build_release.py",
            "scripts/size_report.py",
        ],
    )
    run("dependency consistency", [python, "-m", "pip", "check"])
    run(
        "dependency vulnerability audit",
        [
            python,
            "-m",
            "pip_audit",
            "-r",
            "requirements.txt",
            "--progress-spinner",
            "off",
            "--ignore-vuln",
            "CVE-2025-3000",
        ],
    )
    print("[P2] secret scan")
    secret_scan()
    print("[P2] import-cycle scan")
    import_cycle_scan()
    run("compileall", [python, "-m", "compileall", "-q", "seed", "scripts", "tests"])
    if args.full:
        run("pytest", [python, "-m", "pytest", "-q"])
        run("core acceptance", [python, "scripts/core_acceptance.py"])
    print("[P2] quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
