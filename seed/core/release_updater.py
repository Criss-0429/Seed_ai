"""GitHub Release discovery and verified runtime-update staging."""

from __future__ import annotations

import json
import re
import threading
import urllib.request
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .operations import OperationsManager

OWNER = "Criss-0429"
REPO = "Seed_ai"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
_DOWNLOAD_PREFIX = f"https://github.com/{OWNER}/{REPO}/releases/download/"
_MAX_RUNTIME_BYTES = 1_000_000_000
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


class ReleaseUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateOffer:
    version: str
    file: str
    sha256: str
    bytes: int
    notes: str
    download_url: str

    def public_dict(self) -> dict:
        return {
            "available": True,
            "version": self.version,
            "file": self.file,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "notes": self.notes,
        }


def version_key(value: str) -> tuple:
    match = _VERSION.fullmatch((value or "").strip().lstrip("v"))
    if not match:
        raise ReleaseUpdateError(f"versione non valida: {value!r}")
    major, minor, patch = (int(match.group(i)) for i in range(1, 4))
    suffix = match.group(4)
    if suffix is None:
        return major, minor, patch, 1, ()
    parts = tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.split(r"[.-]", suffix)
    )
    return major, minor, patch, 0, parts


def installed_version(fallback: str) -> str:
    override = os.environ.get("SEED_RELEASE_MANIFEST")
    candidates = [Path(override)] if override else []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent.parent / "release-manifest.json")
    for path in candidates:
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("version")
            version_key(str(value))
            return str(value)
        except (OSError, ValueError, TypeError, json.JSONDecodeError, ReleaseUpdateError):
            continue
    return fallback


class ReleaseUpdater:
    def __init__(
        self,
        operations: OperationsManager,
        current_version: str,
        *,
        enabled: bool,
        open_url: Callable = urllib.request.urlopen,
        api_url: str = API_URL,
    ):
        self.operations = operations
        self.current_version = current_version
        self.enabled = bool(enabled)
        self._open_url = open_url
        self._api_url = api_url
        self._offer: UpdateOffer | None = None
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._status = {
            "state": "idle" if self.enabled else "unavailable",
            "current_version": current_version,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "error": None,
        }

    def status(self) -> dict:
        with self._lock:
            out = dict(self._status)
            if self._offer is not None:
                out["offer"] = self._offer.public_dict()
            out["pending"] = (self.operations.updates / "pending_update.json").is_file()
            return out

    def check(self) -> dict:
        if not self.enabled:
            return self.status()
        with self._lock:
            self._offer = None
        self._set_status(state="checking", error=None)
        try:
            release = self._fetch_json(self._api_url)
            assets = {
                str(asset.get("name")): str(asset.get("browser_download_url"))
                for asset in release.get("assets", []) if isinstance(asset, dict)
            }
            manifest_url = assets.get("release-manifest.json", "")
            self._validate_download_url(manifest_url)
            manifest = self._fetch_json(manifest_url)
            version = str(manifest.get("version") or "")
            if version_key(version) <= version_key(self.current_version):
                with self._lock:
                    self._offer = None
                self._set_status(state="current", latest_version=version, error=None)
                return {"available": False, **self.status()}
            release_assets = manifest.get("release_assets")
            runtime = release_assets.get("runtime") if isinstance(release_assets, dict) else None
            if not isinstance(runtime, dict):
                runtime = manifest.get("update")
            if not isinstance(runtime, dict):
                raise ReleaseUpdateError("runtime update assente dal manifest")
            file_name = str(runtime.get("file") or "")
            expected = str(runtime.get("sha256") or "").lower()
            total = int(runtime.get("bytes") or 0)
            if Path(file_name).name != file_name or not file_name.endswith(".zip"):
                raise ReleaseUpdateError("nome asset runtime non valido")
            if not _SHA256.fullmatch(expected):
                raise ReleaseUpdateError("SHA-256 runtime non valido")
            if total <= 0 or total > _MAX_RUNTIME_BYTES:
                raise ReleaseUpdateError("dimensione runtime non valida")
            asset_url = assets.get(file_name, "")
            self._validate_download_url(asset_url)
            offer = UpdateOffer(
                version=version,
                file=file_name,
                sha256=expected,
                bytes=total,
                notes=str(release.get("body") or "").strip(),
                download_url=asset_url,
            )
            with self._lock:
                self._offer = offer
            self._set_status(
                state="available", latest_version=version,
                total_bytes=total, downloaded_bytes=0, error=None,
            )
            return offer.public_dict()
        except Exception as exc:
            self._set_status(state="error", error=str(exc))
            return {"available": False, **self.status()}

    def start(self, *, owner_confirmed: bool) -> dict:
        if not owner_confirmed:
            raise ReleaseUpdateError("conferma utente richiesta")
        with self._lock:
            if self._offer is None:
                raise ReleaseUpdateError("nessun aggiornamento verificato")
            if self._worker is not None and self._worker.is_alive():
                return dict(self._status)
            offer = self._offer
            self._status.update({
                "state": "downloading", "downloaded_bytes": 0,
                "total_bytes": offer.bytes, "error": None,
            })
            self._worker = threading.Thread(
                target=self._download_and_stage,
                args=(offer,),
                name="seed-release-updater",
                daemon=True,
            )
            self._worker.start()
            return dict(self._status)

    def _download_and_stage(self, offer: UpdateOffer) -> None:
        downloads = self.operations.updates / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        partial = downloads / f"{offer.file}.part"
        complete = downloads / offer.file
        try:
            self._download(offer, partial)
            complete.unlink(missing_ok=True)
            partial.replace(complete)
            staged = self.operations.stage_update(complete, offer.sha256)
            marker = self.operations.schedule_update(staged, owner_confirmed=True)
            complete.unlink(missing_ok=True)
            self._set_status(
                state="ready", downloaded_bytes=offer.bytes,
                staged_package=staged.name, marker=marker.name, error=None,
            )
        except Exception as exc:
            complete.unlink(missing_ok=True)
            self._set_status(state="error", error=str(exc))

    def _download(self, offer: UpdateOffer, target: Path) -> None:
        offset = target.stat().st_size if target.is_file() else 0
        if offset > offer.bytes:
            target.unlink()
            offset = 0
        headers = {"Accept": "application/octet-stream", "User-Agent": "SEED-updater"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(offer.download_url, headers=headers)
        with self._open_url(request, timeout=120) as response:
            status = int(getattr(response, "status", response.getcode()))
            if offset and status == 206:
                content_range = str(response.headers.get("Content-Range") or "")
                if not content_range.startswith(f"bytes {offset}-"):
                    raise ReleaseUpdateError("risposta HTTP Range incoerente")
                mode = "ab"
            elif status == 200:
                offset = 0
                mode = "wb"
            else:
                raise ReleaseUpdateError(f"download HTTP {status}")
            done = offset
            with target.open(mode) as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    done += len(chunk)
                    if done > offer.bytes:
                        raise ReleaseUpdateError("download oltre la dimensione dichiarata")
                    self._set_status(downloaded_bytes=done)
        if target.stat().st_size != offer.bytes:
            raise ReleaseUpdateError("download incompleto")

    def _fetch_json(self, url: str) -> dict:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "SEED-updater"},
        )
        with self._open_url(request, timeout=30) as response:
            payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ReleaseUpdateError("risposta GitHub troppo grande")
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ReleaseUpdateError("risposta GitHub non valida")
        return value

    def _validate_download_url(self, url: str) -> None:
        if not url.startswith(_DOWNLOAD_PREFIX):
            raise ReleaseUpdateError("asset fuori dal repository ufficiale")

    def _set_status(self, **changes) -> None:
        with self._lock:
            self._status.update(changes)
