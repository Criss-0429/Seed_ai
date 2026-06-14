"""Small subprocess used to verify real supervisor health signaling."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.supervisor import default_seed_root, emit_health_signal_from_env  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("healthy", "crash", "slow"), default="healthy")
    args = parser.parse_args()
    if args.mode == "crash":
        return 7
    if args.mode == "slow":
        time.sleep(10)
        return 0
    emit_health_signal_from_env(Path(os.environ.get("SEED_DATA_ROOT", default_seed_root())))
    time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
