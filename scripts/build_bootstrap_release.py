"""Build split GitHub Release assets for the SEED bootstrap strategy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
MAX_PART_BYTES = 1_600_000_000

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

PRESERVED_MODEL_ASSET_KEYS = {
    "privacy-filter": "privacy_model",
    "emotion-wav2vec2": "emotion_model",
    "embedding-mpnet": "embedding_model",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_parts(parts: list[Path]) -> str:
    h = hashlib.sha256()
    for part in parts:
        with part.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def latest_snapshot(root: Path) -> Path:
    snapshots = [path for path in root.iterdir() if path.is_dir()]
    if not snapshots:
        raise RuntimeError(f"checkpoint snapshot missing: {root}")
    return max(snapshots, key=lambda path: path.stat().st_mtime)


def zip_tree(source: Path, target: Path) -> None:
    if target.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())


def split_file(source: Path, version: str, target_dir: Path) -> list[dict[str, str | int]]:
    parts: list[dict[str, str | int]] = []
    existing = sorted(target_dir.glob(f"SEED-models-privacy-filter-{version}.zip.part*"))
    if existing:
        return [{"file": part.name, "sha256": digest(part), "bytes": part.stat().st_size} for part in existing]
    with source.open("rb") as handle:
        index = 1
        while True:
            chunk = handle.read(MAX_PART_BYTES)
            if not chunk:
                break
            part = target_dir / f"SEED-models-privacy-filter-{version}.zip.part{index:02d}"
            part.write_bytes(chunk)
            parts.append({"file": part.name, "sha256": digest(part), "bytes": part.stat().st_size})
            index += 1
    return parts


def build_bootstrap(version: str, target_dir: Path, python_exe: Path) -> Path:
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    userbase = ROOT / "build" / "bootstrap" / "python-userbase"
    userbase.mkdir(parents=True, exist_ok=True)
    env["PYTHONUSERBASE"] = str(userbase)
    subprocess.run(
        [
            str(python_exe),
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--onefile",
            "--icon",
            str(ROOT / "assets" / "seed.ico"),
            "--name",
            "SEED-Bootstrap-Setup-Unsigned",
            "--distpath",
            str(target_dir),
            "--workpath",
            str(ROOT / "build" / "bootstrap"),
            "--specpath",
            str(ROOT / "build" / "bootstrap"),
            str(ROOT / "scripts" / "seed_bootstrap_installer.py"),
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )
    exe = target_dir / "SEED-Bootstrap-Setup-Unsigned.exe"
    if not exe.is_file():
        raise RuntimeError(f"bootstrap build failed: {exe}")
    return exe


def preserved_model_assets(manifest_path: Path) -> dict[str, dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    release_assets = manifest.get("release_assets")
    if not isinstance(release_assets, dict):
        raise RuntimeError(f"release_assets missing from preserve manifest: {manifest_path}")

    preserved: dict[str, dict[str, object]] = {}
    for model_name, asset_key in PRESERVED_MODEL_ASSET_KEYS.items():
        asset = release_assets.get(asset_key)
        if not isinstance(asset, dict):
            raise RuntimeError(f"{asset_key} missing from preserve manifest: {manifest_path}")
        preserved[model_name] = dict(asset)
    return preserved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.3.3-pilot-p2")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--skip-bootstrap", action="store_true")
    parser.add_argument(
        "--preserve-model-assets-from",
        type=Path,
        help="Reuse model release asset metadata from an existing manifest instead of rebuilding model zips.",
    )
    args = parser.parse_args(argv)

    version = args.version
    target = RELEASE / version
    target.mkdir(parents=True, exist_ok=True)
    manifest_path = target / "release-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"release manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    runtime_zip = target / f"SEED-{version}-runtime-update.zip"
    if not runtime_zip.is_file():
        raise RuntimeError(f"runtime update zip missing: {runtime_zip}")
    tester_reset = target / "Reset-SEED-Keep-Memory.ps1"
    if not tester_reset.is_file():
        raise RuntimeError(f"tester reset script missing: {tester_reset}")

    supervisor_dir = DIST / "SEEDSupervisor"
    if not (supervisor_dir / "SEEDSupervisor.exe").is_file():
        raise RuntimeError(f"supervisor build missing: {supervisor_dir}")
    supervisor_zip = target / f"SEED-{version}-supervisor.zip"
    zip_tree(supervisor_dir, supervisor_zip)

    model_assets = preserved_model_assets(args.preserve_model_assets_from) if args.preserve_model_assets_from else {}
    for model_name, source in MODEL_SOURCES.items():
        if model_name in model_assets:
            continue
        if not source.is_dir():
            raise RuntimeError(f"model source missing: {source}")
        actual = latest_snapshot(source) if source.name == "snapshots" else source
        model_zip = target / f"SEED-models-{model_name}-{version}.zip"
        existing_parts = sorted(target.glob(f"SEED-models-privacy-filter-{version}.zip.part*"))
        if model_name == "privacy-filter" and existing_parts:
            parts = [{"file": part.name, "sha256": digest(part), "bytes": part.stat().st_size} for part in existing_parts]
            model_assets[model_name] = {
                "file": model_zip.name,
                "sha256": digest_parts(existing_parts),
                "bytes": sum(part.stat().st_size for part in existing_parts),
                "parts": parts,
            }
            continue
        zip_tree(actual, model_zip)
        if model_name == "privacy-filter" and model_zip.stat().st_size > MAX_PART_BYTES:
            parts = split_file(model_zip, version, target)
            model_assets[model_name] = {
                "file": model_zip.name,
                "sha256": digest(model_zip),
                "bytes": model_zip.stat().st_size,
                "parts": parts,
            }
            model_zip.unlink()
        else:
            model_assets[model_name] = {
                "file": model_zip.name,
                "sha256": digest(model_zip),
                "bytes": model_zip.stat().st_size,
            }

    bootstrap = None
    if not args.skip_bootstrap:
        bootstrap = build_bootstrap(version, target, Path(args.python))

    release_assets = {
        "runtime": {
            "file": runtime_zip.name,
            "sha256": digest(runtime_zip),
            "bytes": runtime_zip.stat().st_size,
            "kind": "runtime-zip",
        },
        "supervisor": {
            "file": supervisor_zip.name,
            "sha256": digest(supervisor_zip),
            "bytes": supervisor_zip.stat().st_size,
            "kind": "supervisor-zip",
        },
        "privacy_model": {**model_assets["privacy-filter"], "kind": "model-zip-split"},
        "embedding_model": {**model_assets["embedding-mpnet"], "kind": "model-zip"},
        "emotion_model": {**model_assets["emotion-wav2vec2"], "kind": "model-zip"},
    }
    if bootstrap is not None:
        release_assets["bootstrap"] = {
            "file": bootstrap.name,
            "sha256": digest(bootstrap),
            "bytes": bootstrap.stat().st_size,
            "kind": "bootstrap-exe",
            "unsigned": True,
        }
    release_assets["tester_reset"] = {
        "file": tester_reset.name,
        "sha256": digest(tester_reset),
        "bytes": tester_reset.stat().st_size,
        "kind": "powershell-support-script",
        "preserves": ["data/seed.db", "data/seed.db-wal", "data/seed.db-shm"],
    }

    manifest.pop("installer", None)
    manifest["release_assets"] = release_assets
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    sums = []
    for path in sorted(target.iterdir()):
        if path.name == f"SEED-{version}-Setup-Unsigned.exe":
            continue
        if path.is_file() and path.name not in {"SHA256SUMS.txt", "SIZE_REPORT.json"}:
            sums.append(f"{digest(path)}  {path.name}\n")
    (target / "SHA256SUMS.txt").write_text("".join(sums), encoding="ascii")
    print(json.dumps({"release": str(target), "assets": [line.split("  ", 1)[1].strip() for line in sums]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
