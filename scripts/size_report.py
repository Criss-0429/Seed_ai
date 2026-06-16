"""Generate deterministic P2 release size report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


BUDGET_THRESHOLD_PERCENT = 5.0


def tree_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def size_regression_verdict(
    installed_bytes: int,
    baseline_bytes: int,
    *,
    reason: str | None = None,
    threshold_percent: float = BUDGET_THRESHOLD_PERCENT,
) -> dict:
    """Verdetto deterministico sul budget di crescita (P2).

    Crescita installata oltre ``threshold_percent`` blocca P2 a meno che non sia
    fornita una motivazione esplicita (ProductionPlan: "crescita superiore al 5%
    richiede motivazione"). Funzione pura: nessun I/O, testabile da sola."""
    baseline = int(baseline_bytes)
    if baseline <= 0:
        raise ValueError("baseline_bytes deve essere positivo")
    delta = round(((int(installed_bytes) - baseline) / baseline) * 100, 3)
    exceeds = delta > float(threshold_percent)
    reason = (reason or "").strip()
    return {
        "installed_bytes": int(installed_bytes),
        "baseline_bytes": baseline,
        "delta_percent": delta,
        "threshold_percent": float(threshold_percent),
        "exceeds_budget": exceeds,
        "reason": reason or None,
        # ammesso se entro budget, oppure oltre ma con motivazione documentata.
        "allowed": (not exceeds) or bool(reason),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--baseline-installer-bytes", type=int, default=3_343_607_920)
    parser.add_argument("--baseline-installed-bytes", type=int, default=5_102_464_829)
    parser.add_argument("--startup-seconds", type=float)
    parser.add_argument("--peak-ram-bytes", type=int)
    parser.add_argument("--reason", default=None,
                        help="motivazione documentata per superare il budget P2")
    args = parser.parse_args(argv)

    release = ROOT / "release" / args.version
    app = release / "app"
    installer = release / f"SEED-{args.version}-Setup-Unsigned.exe"
    update = release / f"SEED-{args.version}-runtime-update.zip"
    components = {path.name: tree_size(path) for path in sorted(app.iterdir()) if path.is_dir()}
    installed = sum(components.values())
    verdict = size_regression_verdict(
        installed, args.baseline_installed_bytes, reason=args.reason)
    report = {
        "schema_version": "seed.size-report.v1",
        "version": args.version,
        "installer_bytes": installer.stat().st_size if installer.is_file() else None,
        "update_bytes": update.stat().st_size if update.is_file() else None,
        "installed_bytes": installed,
        "component_bytes": components,
        "baseline": {
            "installer_bytes": args.baseline_installer_bytes,
            "installed_bytes": args.baseline_installed_bytes,
        },
        "installed_delta_percent": verdict["delta_percent"],
        "budget": verdict,
        "startup_seconds": args.startup_seconds,
        "peak_ram_bytes": args.peak_ram_bytes,
        "notes": [
            "Startup/RAM are measured with the packaged runtime --smoke mode.",
            "Growth above 5 percent blocks P2 unless a documented reason is given "
            "(--reason), which stays owner-approved and auditable.",
        ],
    }
    if not verdict["allowed"]:
        raise RuntimeError(
            "installed size regression exceeds 5 percent without documented reason")

    json_path = release / "SIZE_REPORT.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path = release / "SIZE_REPORT.md"
    rows = "\n".join(f"| {name} | {value:,} |" for name, value in components.items())
    md_path.write_text(
        "# SEED P2 Size Report\n\n"
        f"- Version: `{args.version}`\n"
        f"- Installer bytes: `{report['installer_bytes']}`\n"
        f"- Installed bytes: `{installed}`\n"
        f"- Baseline installed bytes: `{args.baseline_installed_bytes}`\n"
        f"- Installed delta: `{report['installed_delta_percent']}%`\n"
        f"- Startup seconds: `{report['startup_seconds']}`\n"
        f"- Peak RAM bytes: `{report['peak_ram_bytes']}`\n\n"
        "| Component | Bytes |\n|---|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
