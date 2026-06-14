"""Build P1 tester release layout, update ZIP, manifest, and hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASES = ROOT / "release"

MODEL_SOURCES = {
    "privacy-filter": Path.home() / ".opf" / "privacy_filter",
    "emotion-wav2vec2": Path.home() / ".cache" / "huggingface" / "hub"
    / "models--superb--wav2vec2-base-superb-er" / "snapshots",
    "embedding-mpnet": Path.home() / ".cache" / "huggingface" / "hub"
    / "models--sentence-transformers--paraphrase-multilingual-mpnet-base-v2" / "snapshots",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def latest_snapshot(root: Path) -> Path:
    snapshots = [path for path in root.iterdir() if path.is_dir()]
    if not snapshots:
        raise RuntimeError(f"checkpoint snapshot missing: {root}")
    return max(snapshots, key=lambda path: path.stat().st_mtime)


def copy_models(target: Path) -> dict[str, int]:
    sizes = {}
    for name, source in MODEL_SOURCES.items():
        if not source.is_dir():
            raise RuntimeError(f"required ML checkpoint missing: {source}")
        actual = latest_snapshot(source) if source.name == "snapshots" else source
        destination = target / name
        shutil.copytree(actual, destination)
        sizes[name] = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
    return sizes


def build_pyinstaller() -> None:
    for spec in ("build/seed.spec", "build/supervisor.spec"):
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec],
            cwd=ROOT, check=True)


def zip_tree(source: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--schema-version", type=int, default=1)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)

    if not args.skip_build:
        build_pyinstaller()
    runtime = DIST / "SEED"
    supervisor = DIST / "SEEDSupervisor"
    if not (runtime / "SEED.exe").is_file() or not (supervisor / "SEEDSupervisor.exe").is_file():
        raise RuntimeError("onedir builds missing")

    target = RELEASES / args.version
    shutil.rmtree(target, ignore_errors=True)
    (target / "app").mkdir(parents=True)
    shutil.copytree(runtime, target / "app" / "runtime")
    shutil.copytree(supervisor, target / "app" / "supervisor")
    model_sizes = copy_models(target / "app" / "models")
    shutil.copy2(ROOT / "installer" / "TESTER_GUIDE.md", target / "TESTER_GUIDE.md")

    update_zip = target / f"SEED-{args.version}-runtime-update.zip"
    zip_tree(target / "app" / "runtime", update_zip)
    file_hashes = hashes(target / "app")
    manifest = {
        "schema_version": "seed.release.v1",
        "version": args.version,
        "data_schema_version": args.schema_version,
        "created_at": time.time(),
        "unsigned": True,
        "layout": {"runtime": "app/runtime", "supervisor": "app/supervisor", "models": "app/models"},
        "files": file_hashes,
        "update": {"file": update_zip.name, "sha256": digest(update_zip), "kind": "runtime-zip"},
        "model_bytes": model_sizes,
        "installed_bytes": sum((target / "app" / path).stat().st_size for path in file_hashes),
    }
    manifest_path = target / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (target / "SHA256SUMS.txt").write_text(
        f"{digest(manifest_path)}  {manifest_path.name}\n"
        f"{digest(update_zip)}  {update_zip.name}\n",
        encoding="ascii")
    print(json.dumps({
        "release": str(target), "files": len(file_hashes),
        "installed_bytes": manifest["installed_bytes"],
        "update_sha256": manifest["update"]["sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
