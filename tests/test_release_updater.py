from __future__ import annotations

import hashlib
import io
import json
import time

import pytest

from seed.core.operations import OperationsManager
from seed.core.release_updater import (
    API_URL,
    ReleaseUpdateError,
    ReleaseUpdater,
    version_key,
)


MANIFEST_URL = (
    "https://github.com/Criss-0429/Seed_ai/releases/download/"
    "v0.3.1-pilot-p2/release-manifest.json"
)
RUNTIME_URL = (
    "https://github.com/Criss-0429/Seed_ai/releases/download/"
    "v0.3.1-pilot-p2/SEED-0.3.1-pilot-p2-runtime-update.zip"
)


class Response:
    def __init__(self, data: bytes, status: int = 200, headers: dict | None = None):
        self._stream = io.BytesIO(data)
        self.status = status
        self.headers = headers or {}

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def payloads(runtime: bytes, version: str = "0.3.1-pilot-p2") -> tuple[bytes, bytes]:
    release = {
        "body": "Correzioni stabilita e memoria.",
        "assets": [
            {"name": "release-manifest.json", "browser_download_url": MANIFEST_URL},
            {"name": "SEED-0.3.1-pilot-p2-runtime-update.zip",
             "browser_download_url": RUNTIME_URL},
        ],
    }
    manifest = {
        "version": version,
        "release_assets": {"runtime": {
            "file": "SEED-0.3.1-pilot-p2-runtime-update.zip",
            "sha256": hashlib.sha256(runtime).hexdigest(),
            "bytes": len(runtime),
        }},
    }
    return json.dumps(release).encode(), json.dumps(manifest).encode()


def opener(runtime: bytes, *, version: str = "0.3.1-pilot-p2"):
    release, manifest = payloads(runtime, version)

    def _open(request, timeout=0):
        url = request.full_url
        if url == API_URL:
            return Response(release)
        if url == MANIFEST_URL:
            return Response(manifest)
        if url == RUNTIME_URL:
            return Response(runtime)
        raise AssertionError(url)

    return _open


def wait_done(updater: ReleaseUpdater) -> dict:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        status = updater.status()
        if status["state"] not in {"downloading", "checking"}:
            return status
        time.sleep(0.01)
    raise AssertionError("updater thread did not finish")


def test_version_ordering():
    assert version_key("0.3.1-pilot-p2") > version_key("0.3.0-pilot-p2")
    assert version_key("0.3.1") > version_key("0.3.1-rc.2")
    with pytest.raises(ReleaseUpdateError):
        version_key("latest")


def test_check_current_does_not_offer_download(tmp_path):
    runtime = b"zip"
    updater = ReleaseUpdater(
        OperationsManager(tmp_path), "0.3.1-pilot-p2", enabled=True,
        open_url=opener(runtime),
    )
    result = updater.check()
    assert result["available"] is False
    assert result["state"] == "current"


def test_check_download_stage_and_schedule(tmp_path):
    runtime = b"PK\x03\x04runtime-update"
    updater = ReleaseUpdater(
        OperationsManager(tmp_path), "0.3.0-pilot-p2", enabled=True,
        open_url=opener(runtime),
    )
    offer = updater.check()
    assert offer["available"] is True and offer["bytes"] == len(runtime)
    with pytest.raises(ReleaseUpdateError, match="conferma"):
        updater.start(owner_confirmed=False)
    updater.start(owner_confirmed=True)
    status = wait_done(updater)
    assert status["state"] == "ready" and status["pending"] is True
    marker = json.loads((tmp_path / "operations/updates/pending_update.json").read_text())
    assert marker["package"].endswith(".zip")
    assert marker["sha256"] == hashlib.sha256(runtime).hexdigest()


def test_resume_uses_range_and_appends(tmp_path):
    runtime = b"0123456789"
    release, manifest = payloads(runtime)
    partial = (tmp_path / "operations/updates/downloads" /
               "SEED-0.3.1-pilot-p2-runtime-update.zip.part")
    partial.parent.mkdir(parents=True)
    partial.write_bytes(runtime[:4])
    seen = {}

    def _open(request, timeout=0):
        if request.full_url == API_URL:
            return Response(release)
        if request.full_url == MANIFEST_URL:
            return Response(manifest)
        seen["range"] = request.headers.get("Range")
        return Response(runtime[4:], 206, {"Content-Range": "bytes 4-9/10"})

    updater = ReleaseUpdater(
        OperationsManager(tmp_path), "0.3.0-pilot-p2", enabled=True, open_url=_open)
    updater.check()
    updater.start(owner_confirmed=True)
    assert wait_done(updater)["state"] == "ready"
    assert seen["range"] == "bytes=4-"


def test_hash_mismatch_fails_without_marker(tmp_path):
    runtime = b"actual"
    release, manifest_bytes = payloads(b"expect")

    def _open(request, timeout=0):
        return Response({API_URL: release, MANIFEST_URL: manifest_bytes}.get(
            request.full_url, runtime))

    updater = ReleaseUpdater(
        OperationsManager(tmp_path), "0.3.0-pilot-p2", enabled=True, open_url=_open)
    updater.check()
    updater.start(owner_confirmed=True)
    status = wait_done(updater)
    assert status["state"] == "error" and "digest" in status["error"]
    assert not (tmp_path / "operations/updates/pending_update.json").exists()


def test_manifest_asset_outside_official_repo_is_blocked(tmp_path):
    release = json.dumps({"assets": [{
        "name": "release-manifest.json", "browser_download_url": "https://evil.invalid/x"
    }]}).encode()
    updater = ReleaseUpdater(
        OperationsManager(tmp_path), "0.3.0-pilot-p2", enabled=True,
        open_url=lambda *_args, **_kwargs: Response(release),
    )
    result = updater.check()
    assert result["state"] == "error" and "repository ufficiale" in result["error"]
