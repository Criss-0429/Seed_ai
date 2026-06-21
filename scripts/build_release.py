"""Build P1 tester release layout, update ZIP, manifest, and hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    "emotion-wav2vec2": Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--superb--wav2vec2-base-superb-er"
    / "snapshots",
    "embedding-mpnet": Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--paraphrase-multilingual-mpnet-base-v2"
    / "snapshots",
}

PRUNE_DIRECTORY_NAMES = {"__pycache__", "test", "tests", "testing"}
PRUNE_RUNTIME_PACKAGES = {"librosa", "llvmlite", "llvmlite.libs", "numba"}


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


def copy_models(target: Path, include: set[str]) -> dict[str, int]:
    """Bundla solo i modelli in `include`. Default: privacy-filter (l'unico usato
    dalla config di default). embedding/emotion sono OFF di default: bundlarli
    gonfia l'installer di ~1.8GB per nulla, percio' si scaricano on-demand se
    l'utente li attiva."""
    sizes = {}
    for name, source in MODEL_SOURCES.items():
        if name not in include:
            continue
        if not source.is_dir():
            raise RuntimeError(f"required ML checkpoint missing: {source}")
        actual = latest_snapshot(source) if source.name == "snapshots" else source
        destination = target / name
        shutil.copytree(
            actual,
            destination,
            ignore=shutil.ignore_patterns(".cache", "README.md", "*.md"),
        )
        sizes[name] = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
    return sizes


def prune_runtime(root: Path) -> dict[str, int]:
    removed = {"files": 0, "bytes": 0}
    candidates = [
        path
        for path in root.rglob("*")
        if path.is_dir()
        and (
            path.name in PRUNE_DIRECTORY_NAMES
            or path.name in PRUNE_RUNTIME_PACKAGES
            or any(path.name.startswith(f"{name}-") for name in PRUNE_RUNTIME_PACKAGES)
        )
    ]
    for path in sorted(candidates, key=lambda item: len(item.parts), reverse=True):
        if not path.exists():
            continue
        files = [item for item in path.rglob("*") if item.is_file()]
        removed["files"] += len(files)
        removed["bytes"] += sum(item.stat().st_size for item in files)
        shutil.rmtree(path)
    return removed


def component_sizes(root: Path) -> dict[str, int]:
    return {
        path.name: sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
        for path in sorted(root.iterdir())
        if path.is_dir()
    }


def build_pyinstaller() -> None:
    for spec in (
        "packaging/pyinstaller/seed.spec",
        "packaging/pyinstaller/supervisor.spec",
    ):
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec],
            cwd=ROOT,
            check=True,
        )


def zip_tree(source: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())


def finalize_installer(target: Path, version: str) -> None:
    manifest_path = target / "release-manifest.json"
    update_zip = target / f"SEED-{version}-runtime-update.zip"
    installer = target / f"SEED-{version}-Setup-Unsigned.exe"
    if not manifest_path.is_file() or not update_zip.is_file() or not installer.is_file():
        raise RuntimeError("release manifest, update ZIP, or compiled installer missing")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["installer"] = {
        "file": installer.name,
        "sha256": digest(installer),
        "unsigned": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (target / "SHA256SUMS.txt").write_text(
        f"{digest(manifest_path)}  {manifest_path.name}\n"
        f"{digest(update_zip)}  {update_zip.name}\n"
        f"{digest(installer)}  {installer.name}\n",
        encoding="ascii",
    )
    print(json.dumps({"installer": str(installer), "sha256": manifest["installer"]["sha256"]}))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--schema-version", type=int, default=1)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--finalize-installer", action="store_true")
    # Modelli ML opzionali (default OFF): bundlarli gonfia l'installer.
    parser.add_argument("--with-embedding", action="store_true",
                        help="bundla il modello embedding (~1.1GB)")
    parser.add_argument("--with-emotion", action="store_true",
                        help="bundla il modello emotion wav2vec2 (~0.7GB)")
    args = parser.parse_args(argv)

    target = RELEASES / args.version
    if args.finalize_installer:
        finalize_installer(target, args.version)
        return 0

    if not args.skip_build:
        build_pyinstaller()
    runtime = DIST / "SEED"
    supervisor = DIST / "SEEDSupervisor"
    if not (runtime / "SEED.exe").is_file() or not (supervisor / "SEEDSupervisor.exe").is_file():
        raise RuntimeError("onedir builds missing")

    shutil.rmtree(target, ignore_errors=True)
    (target / "app").mkdir(parents=True)
    shutil.copytree(runtime, target / "app" / "runtime")
    shutil.copytree(supervisor, target / "app" / "supervisor")
    pruned = prune_runtime(target / "app" / "runtime")
    supervisor_pruned = prune_runtime(target / "app" / "supervisor")
    pruned["files"] += supervisor_pruned["files"]
    pruned["bytes"] += supervisor_pruned["bytes"]
    include = {"privacy-filter"}
    if args.with_embedding:
        include.add("embedding-mpnet")
    if args.with_emotion:
        include.add("emotion-wav2vec2")
    model_sizes = copy_models(target / "app" / "models", include)
    shutil.copy2(ROOT / "installer" / "TESTER_GUIDE.md", target / "TESTER_GUIDE.md")
    shutil.copy2(
        ROOT / "installer" / "Reset-SEED-Keep-Memory.ps1",
        target / "Reset-SEED-Keep-Memory.ps1",
    )

    update_zip = target / f"SEED-{args.version}-runtime-update.zip"
    zip_tree(target / "app" / "runtime", update_zip)
    file_hashes = hashes(target / "app")
    manifest = {
        "schema_version": "seed.release.v1",
        "version": args.version,
        "data_schema_version": args.schema_version,
        "created_at": time.time(),
        "unsigned": True,
        "features": {
            "voice": {
                "provider": "elevenlabs",
                "byok": True,
                "optional": True,
                "skippable": True,
                "bundled_key": False,
            },
        },
        "layout": {
            "runtime": "app/runtime",
            "supervisor": "app/supervisor",
            "models": "app/models",
        },
        "files": file_hashes,
        "update": {"file": update_zip.name, "sha256": digest(update_zip), "kind": "runtime-zip"},
        "model_bytes": model_sizes,
        "component_bytes": component_sizes(target / "app"),
        "pruned": pruned,
        "installed_bytes": sum((target / "app" / path).stat().st_size for path in file_hashes),
    }
    manifest_path = target / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (target / "SHA256SUMS.txt").write_text(
        f"{digest(manifest_path)}  {manifest_path.name}\n{digest(update_zip)}  {update_zip.name}\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "release": str(target),
                "files": len(file_hashes),
                "installed_bytes": manifest["installed_bytes"],
                "update_sha256": manifest["update"]["sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
