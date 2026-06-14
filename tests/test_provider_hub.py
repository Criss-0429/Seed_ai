"""P0 Provider Hub: BYOK, DPAPI-at-rest, gate and Ollama-only fallback."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.model_router import ModelRouter  # noqa: E402
from seed.core.provider_hub import ProviderHub, ProviderHubError  # noqa: E402


class Response:
    def __init__(self, payload, ok=True):
        self.payload = payload
        self.ok = ok

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("401")

    def json(self):
        return self.payload


class FakeHTTP:
    def __init__(self, models=None, fail=False):
        self.models = models or ["gemma4:31b", "qwen3-coder-next", "gpt-oss:120b",
                                 "nemotron-3-super"]
        self.fail = fail
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.fail:
            return Response({}, ok=False)
        if method == "GET":
            return Response({"data": [{"id": model} for model in self.models]})
        return Response({"choices": [{"message": {"content": "OK"}}]})


def test_profile_is_validated_encrypted_and_public_output_has_no_key(tmp_path):
    events = []
    hub = ProviderHub(
        tmp_path / "providers.json", request=FakeHTTP(),
        audit=lambda event, payload: events.append((event, payload)))

    profile = hub.validate_and_save("ollama_cloud", "super-secret-key")
    raw = hub.path.read_text(encoding="utf-8")
    status = hub.status()

    assert profile["validated"] and profile["active"]
    assert hub.ready is True
    assert "super-secret-key" not in raw
    assert "super-secret-key" not in json.dumps(status)
    assert hub.runtime().api_key == "super-secret-key"
    assert events[-1] == ("provider_validated", {"provider": "ollama_cloud", "ok": True})


def test_invalid_key_is_not_saved(tmp_path):
    hub = ProviderHub(tmp_path / "providers.json", request=FakeHTTP(fail=True))
    with pytest.raises(RuntimeError, match="401"):
        hub.validate_and_save("openrouter", "bad")
    assert hub.ready is False
    assert not hub.path.exists()


def test_roles_must_exist_in_discovered_catalog(tmp_path):
    hub = ProviderHub(tmp_path / "providers.json", request=FakeHTTP(models=["model-a"]))
    with pytest.raises(ProviderHubError, match="models not available"):
        hub.validate_and_save(
            "vercel", "key",
            roles={"conversation": "missing-model"})


def test_revoke_active_provider_closes_gate(tmp_path):
    hub = ProviderHub(tmp_path / "providers.json", request=FakeHTTP())
    hub.validate_and_save("ollama_cloud", "key")
    hub.revoke("ollama_cloud")
    assert hub.ready is False
    assert hub.status()["active_provider"] == ""


class FakeClient:
    def __init__(self, fail=False):
        self.has_key = True
        self.fail = fail
        self.calls = []

    def chat(self, messages, *, model=None, **kwargs):
        self.calls.append(model)
        if self.fail:
            raise RuntimeError("provider down")
        return LLMResponse(text=f"ok:{model}")


def test_model_router_external_fallback_is_explicit_ollama_only():
    primary = FakeClient(fail=True)
    ollama = FakeClient()
    router = ModelRouter(
        primary, {"conversation": "payg-model"},
        provider="openrouter",
        ollama_fallback_client=ollama,
        ollama_fallback_roles={"conversation": "gemma4:31b"})

    assert router.invoke("conversation", []).text == "ok:gemma4:31b"
    assert primary.calls == ["payg-model"]
    assert ollama.calls == ["gemma4:31b"]


def test_required_provider_blocks_personal_onboarding_but_not_local_recovery(
    tmp_path, monkeypatch
):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    cfg = SeedConfig()
    cfg.provider_hub.required = True
    app = SeedApp(cfg)

    provider_prompt = app.handle_message("accetto")
    still_blocked = app.handle_message("Sono una persona e questo e personale")
    local = app.handle_message(":daemon")

    assert app.onboarding.state["phase"] == "provider"
    assert "provider BYOK" in provider_prompt
    assert "provider BYOK" in still_blocked
    assert "tick_count" in local
    app.memory.close()


def test_validation_releases_provider_onboarding_gate(tmp_path, monkeypatch):
    root = tmp_path / "SEED"
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: root)
    cfg = SeedConfig()
    cfg.provider_hub.required = True
    app = SeedApp(cfg)
    app.provider_hub._request = FakeHTTP()
    app.handle_message("accetto")

    result = app.ui_provider_validate("ollama_cloud", "key")
    next_prompt = app.handle_message("continua")

    assert result["ok"] is True
    assert app.provider_hub.ready is True
    assert app.onboarding.state["phase"] == "story"
    assert "Parlami" in next_prompt
    app.memory.close()
