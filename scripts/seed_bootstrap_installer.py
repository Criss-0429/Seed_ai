"""SEED bootstrap installer for tester GitHub Releases.

The bootstrap is intentionally small. It downloads release assets from the same
GitHub Release, verifies SHA-256 hashes from release-manifest.json, extracts the
runtime/supervisor/model payloads under LocalAppData, creates shortcuts, and
starts SEED through the supervisor.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

OWNER = "Criss-0429"
REPO = "Seed_ai"
TAG = "v0.3.0-pilot-p2"
VERSION = "0.3.0-pilot-p2"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG}"


def log(message: str) -> None:
    print(f"[SEED bootstrap] {message}", flush=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "SEED-bootstrap"})
    with urllib.request.urlopen(req, timeout=120) as response, target.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r[SEED bootstrap] download {target.name}: {done * 100 // total}%", end="", flush=True)
        if total:
            print()


def asset_map(release: dict) -> dict[str, str]:
    return {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}


def extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(destination)


def verify(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual.lower() != expected.lower():
        raise RuntimeError(f"hash mismatch for {path.name}: expected {expected}, got {actual}")


def powershell(script: str) -> None:
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )


def create_shortcut(path: Path, target: Path, args: str, icon: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut('{path}')
    $shortcut.TargetPath = '{target}'
    $shortcut.Arguments = '{args}'
    $shortcut.WorkingDirectory = '{target.parent}'
    $shortcut.IconLocation = '{icon}'
    $shortcut.Save()
    """
    powershell(script)


def main() -> int:
    install_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "SEED"
    data_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "SEED"
    log(f"install root: {install_root}")
    data_root.mkdir(parents=True, exist_ok=True)

    release = fetch_json(API)
    assets = asset_map(release)
    manifest_name = "release-manifest.json"
    if manifest_name not in assets:
        raise RuntimeError("release-manifest.json missing from GitHub Release")

    with tempfile.TemporaryDirectory(prefix="seed-bootstrap-") as tmp_name:
        tmp = Path(tmp_name)
        manifest_path = tmp / manifest_name
        log("download manifest")
        download(assets[manifest_name], manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        release_assets = manifest.get("release_assets", {})

        required = ["runtime", "supervisor", "embedding_model", "emotion_model"]
        for key in required:
            name = release_assets[key]["file"]
            if name not in assets:
                raise RuntimeError(f"required release asset missing: {name}")

        install_root.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(install_root / "runtime", ignore_errors=True)
        shutil.rmtree(install_root / "supervisor", ignore_errors=True)
        (install_root / "models").mkdir(parents=True, exist_ok=True)

        for key, destination in (
            ("runtime", install_root / "runtime"),
            ("supervisor", install_root / "supervisor"),
            ("embedding_model", install_root / "models" / "embedding-mpnet"),
            ("emotion_model", install_root / "models" / "emotion-wav2vec2"),
        ):
            spec = release_assets[key]
            archive = tmp / spec["file"]
            log(f"download {spec['file']}")
            download(assets[spec["file"]], archive)
            verify(archive, spec["sha256"])
            shutil.rmtree(destination, ignore_errors=True)
            log(f"extract {spec['file']}")
            extract_zip(archive, destination)

        privacy = release_assets.get("privacy_model")
        if privacy:
            parts = privacy.get("parts", [])
            if not parts:
                raise RuntimeError("privacy_model declared without parts")
            joined = tmp / privacy["file"]
            with joined.open("wb") as out:
                for part in parts:
                    name = part["file"]
                    if name not in assets:
                        raise RuntimeError(f"required release asset missing: {name}")
                    part_path = tmp / name
                    log(f"download {name}")
                    download(assets[name], part_path)
                    verify(part_path, part["sha256"])
                    with part_path.open("rb") as inp:
                        shutil.copyfileobj(inp, out, 1024 * 1024)
            verify(joined, privacy["sha256"])
            destination = install_root / "models" / "privacy-filter"
            shutil.rmtree(destination, ignore_errors=True)
            log(f"extract {privacy['file']}")
            extract_zip(joined, destination)

        (install_root / "release-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    supervisor = install_root / "supervisor" / "SEEDSupervisor.exe"
    runtime = install_root / "runtime" / "SEED.exe"
    if not supervisor.is_file() or not runtime.is_file():
        raise RuntimeError("installed SEED runtime or supervisor missing")

    start_menu = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "SEED.lnk"
    desktop = Path.home() / "Desktop" / "SEED.lnk"
    args = f'--boot --runtime "{runtime}"'
    create_shortcut(start_menu, supervisor, args, runtime)
    create_shortcut(desktop, supervisor, args, runtime)

    log("start SEED")
    subprocess.Popen([str(supervisor), "--boot", "--runtime", str(runtime)], cwd=str(supervisor.parent))
    log(f"installed SEED {VERSION}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError, OSError, zipfile.BadZipFile) as exc:
        print(f"\n[SEED bootstrap] ERROR: {exc}", file=sys.stderr)
        input("Premi Invio per chiudere.")
        raise SystemExit(1)
