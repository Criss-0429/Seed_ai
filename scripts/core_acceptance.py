"""CLI for the isolated SEED S1-S5 practical acceptance run."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.acceptance import CoreAcceptanceError, run_core_acceptance  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="empty directory for artifacts; default creates a temporary directory",
    )
    args = parser.parse_args()
    root = args.output or Path(tempfile.mkdtemp(prefix="seed-core-acceptance-"))
    try:
        report = run_core_acceptance(root)
    except CoreAcceptanceError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": report["status"],
                "checks": len(report["checks"]),
                "report": str(root / "core_acceptance_report.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
