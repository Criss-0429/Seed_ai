"""Restricted-process runner. Executes source with filesystem access scoped to CWD."""

from __future__ import annotations

import builtins
import io
import json
import os
import sys
from pathlib import Path


def _under(path: object, root: Path) -> Path:
    if isinstance(path, int):
        raise PermissionError("file descriptors are not available in isolated process")
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = Path(os.path.abspath(os.path.normpath(str(candidate))))
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError("isolated process path outside workspace") from exc
    return resolved


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("tool path required")
    source_path = Path(sys.argv[1]).resolve()
    source = source_path.read_text(encoding="utf-8")
    root = Path.cwd().resolve()
    real_open, real_io_open, real_os_open = builtins.open, io.open, os.open
    real_scandir, real_stat, real_lstat = os.scandir, os.stat, os.lstat

    def guarded_open(file, *args, **kwargs):
        return real_open(_under(file, root), *args, **kwargs)

    def guarded_os_open(file, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None:
            raise PermissionError("dir_fd not available in isolated process")
        return real_os_open(_under(file, root), flags, mode)

    def guarded_scandir(path="."):
        return real_scandir(_under(path, root))

    def guarded_stat(path, *args, **kwargs):
        return real_stat(_under(path, root), *args, **kwargs)

    def guarded_lstat(path, *args, **kwargs):
        return real_lstat(_under(path, root), *args, **kwargs)

    builtins.open = guarded_open
    io.open = guarded_open
    os.open = guarded_os_open
    os.chdir = lambda path: (_ for _ in ()).throw(PermissionError("chdir blocked"))
    os.scandir = guarded_scandir
    os.listdir = lambda path=".": [entry.name for entry in guarded_scandir(path)]
    os.stat = guarded_stat
    os.lstat = guarded_lstat
    os.access = lambda path, mode, *a, **k: False
    os.readlink = lambda path, *a, **k: (_ for _ in ()).throw(PermissionError("readlink blocked"))
    os.symlink = lambda *a, **k: (_ for _ in ()).throw(PermissionError("symlink blocked"))
    os.remove = lambda path, *a, **k: (_ for _ in ()).throw(PermissionError("remove blocked"))
    os.unlink = os.remove
    namespace = {"__name__": "__main__", "__file__": str(source_path),
                 "__builtins__": builtins.__dict__}
    exec(compile(source, str(source_path), "exec"), namespace, namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
