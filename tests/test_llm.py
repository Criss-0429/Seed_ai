"""LLMClient: guardia redatto, retry/backoff su errori transitori.
Offline: requests.post mockato, time.sleep azzerato."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import llm as llm_mod  # noqa: E402
from seed.core.llm import LLMClient  # noqa: E402


class FakeResp:
    def __init__(self, status=200, json_data=None, headers=None):
        self.status_code = status
        self._json = json_data or {
            "choices": [{"message": {"content": "ok"}}], "usage": {}}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"http {self.status_code}")

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(llm_mod.time, "sleep", lambda *_: None)


def _client(**kw):
    return LLMClient("https://x/v1", "key", "model", **kw)


def test_requires_redacted_flag():
    with pytest.raises(PermissionError):
        _client().chat([{"role": "user", "content": "hi"}])


def test_retries_transient_then_succeeds(monkeypatch):
    seq = [FakeResp(503), FakeResp(500), FakeResp(200)]
    calls = {"n": 0}

    def fake_post(*a, **k):
        r = seq[calls["n"]]
        calls["n"] += 1
        return r

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)
    out = _client(retries=2, backoff=0).chat([], redacted=True)
    assert out.text == "ok"
    assert calls["n"] == 3   # 2 transient + 1 success


def test_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(llm_mod.requests, "post", lambda *a, **k: FakeResp(503))
    with pytest.raises(requests.HTTPError):
        _client(retries=2, backoff=0).chat([], redacted=True)


def test_retries_on_connection_error(monkeypatch):
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.ConnectionError("reset")
        return FakeResp(200)

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)
    out = _client(retries=2, backoff=0).chat([], redacted=True)
    assert out.text == "ok" and calls["n"] == 2


def test_4xx_not_retried(monkeypatch):
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        return FakeResp(400)

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)
    with pytest.raises(requests.HTTPError):
        _client(retries=3, backoff=0).chat([], redacted=True)
    assert calls["n"] == 1   # 400 non si ritenta
