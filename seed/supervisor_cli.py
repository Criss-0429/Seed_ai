"""Command-line boundary for SEED Stable Boot Supervisor."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from .supervisor import (
    BootSupervisor,
    SubprocessRuntimeLauncher,
    SupervisorError,
    default_seed_root,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_seed_root())
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--register-current", metavar="VERSION")
    actions.add_argument("--recover", metavar="VERSION")
    actions.add_argument("--boot", action="store_true")
    parser.add_argument("--reason", default="manual supervisor recovery")
    parser.add_argument("--runtime", type=Path, help="runtime executable used by --boot")
    parser.add_argument("--background", action="store_true",
                        help="launch runtime hidden with heartbeat active")
    parser.add_argument("--wait-pid", type=int, default=0,
                        help="wait for the current runtime process before updating")
    args = parser.parse_args(argv)
    try:
        supervisor = BootSupervisor(args.root)
        if args.register_current:
            path = supervisor.register_current_version(args.register_current)
            output = {"status": "registered", "version_id": args.register_current,
                      "path": path.as_posix()}
        elif args.recover:
            supervisor.manual_recover(args.recover, args.reason)
            output = {"status": "recovered", "version_id": args.recover}
        else:
            if args.runtime is None:
                raise SupervisorError("--runtime is required with --boot")
            if args.wait_pid:
                _wait_for_process_exit(args.wait_pid)
            # Updater reale: applica un eventuale update staged prima del boot.
            update = supervisor.apply_pending_update(args.runtime)
            result = supervisor.boot(
                SubprocessRuntimeLauncher(
                    [str(args.runtime), *(["--background"] if args.background else [])],
                    seed_root=args.root)
            )
            if update and update.get("applied") and result.status != "healthy":
                rollback = supervisor.rollback_runtime_update(update)
                retry = supervisor.boot(
                    SubprocessRuntimeLauncher(
                        [str(args.runtime), *(["--background"] if args.background else [])],
                        seed_root=args.root)
                )
                output = retry.public_dict()
                output["pending_update"] = update
                output["update_rollback"] = rollback
                print(json.dumps(output, ensure_ascii=False))
                return 0 if retry.status == "healthy" else 1
            output = result.public_dict()
            if update is not None:
                output["pending_update"] = update
        print(json.dumps(output, ensure_ascii=False))
        return 0 if output["status"] in {"registered", "recovered", "healthy"} else 1
    except (OSError, SupervisorError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2


def _wait_for_process_exit(pid: int, timeout_seconds: float = 60.0) -> None:
    if pid <= 0 or pid == os.getpid():
        raise SupervisorError("invalid --wait-pid")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.1)
    raise SupervisorError("runtime did not exit before update timeout")


if __name__ == "__main__":
    raise SystemExit(main())
