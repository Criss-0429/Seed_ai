"""P0 Provider Hub: profili BYOK separati, cifrati e validati.

Le credenziali restano sotto ``core_config`` cifrate con DPAPI su Windows.
Il file persistito contiene solo metadati, catalogo modelli e ciphertext.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

from . import forbidden
from .dpapi import decrypt_str, encrypt_str

log = logging.getLogger("seed.provider_hub")

SCHEMA_VERSION = "seed.provider-hub.v1"

# Model ids che NON sono modelli di chat: non devono mai finire sul ruolo
# conversation (era il bug del fallback su models[0] in ordine alfabetico).
_NON_CHAT_ID = re.compile(
    r"(embed|embedding|rerank|reranker|whisper|tts|speech|audio|moderation|"
    r"guard|vision|image|clip|bge|nomic|minilm)",
    re.IGNORECASE,
)
ROLE_NAMES = (
    "conversation",
    "reflection",
    "tool_builder",
    "design_reviewer",
    "design_reviewer_fallback",
)

PROVIDERS = {
    "ollama_cloud": {
        "label": "Ollama Cloud",
        "base_url": "https://ollama.com/v1",
        "dashboard_url": "https://ollama.com/settings/keys",
        "pricing": "free_available",
        "automatic_fallback_target": True,
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "dashboard_url": "https://openrouter.ai/settings/keys",
        "pricing": "payg",
        "automatic_fallback_target": False,
    },
    "vercel": {
        "label": "Vercel AI Gateway",
        "base_url": "https://ai-gateway.vercel.sh/v1",
        "dashboard_url": "https://vercel.com/ai-gateway",
        "pricing": "payg",
        "automatic_fallback_target": False,
    },
}

_PRESET_CANDIDATES = {
    "ollama_cloud": {
        "conversation": ("gpt-oss:120b", "gpt-oss:20b", "glm-4.6"),
        "reflection": ("gpt-oss:120b", "deepseek-v3.1:671b"),
        "tool_builder": ("qwen3-coder:480b", "gpt-oss:120b"),
        "design_reviewer": ("gpt-oss:120b",),
        "design_reviewer_fallback": ("deepseek-v3.1:671b",),
    },
    "openrouter": {
        "conversation": ("openai/gpt-4.1-mini", "google/gemini-2.5-flash"),
        "reflection": ("openai/gpt-4.1",),
        "tool_builder": ("qwen/qwen3-coder",),
        "design_reviewer": ("openai/gpt-4.1",),
        "design_reviewer_fallback": ("google/gemini-2.5-pro",),
    },
    "vercel": {
        "conversation": ("openai/gpt-4.1-mini", "google/gemini-2.5-flash"),
        "reflection": ("openai/gpt-4.1",),
        "tool_builder": ("qwen/qwen3-coder",),
        "design_reviewer": ("openai/gpt-4.1",),
        "design_reviewer_fallback": ("google/gemini-2.5-pro",),
    },
}


class ProviderHubError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderRuntime:
    provider: str
    base_url: str
    api_key: str
    roles: dict[str, str]


def provider_hub_path() -> Path:
    return forbidden.core_config_dir() / "providers.json"


class ProviderHub:
    def __init__(
        self,
        path: Path | None = None,
        *,
        request: Callable[..., Any] | None = None,
        audit: Callable[[str, dict], None] | None = None,
    ):
        self.path = path or provider_hub_path()
        self._request = request or requests.request
        self._audit = audit

    def status(self) -> dict:
        data = self._load()
        profiles = []
        for provider, profile in sorted(data["profiles"].items()):
            spec = PROVIDERS[provider]
            profiles.append(
                {
                    "provider": provider,
                    "label": spec["label"],
                    "pricing": spec["pricing"],
                    "dashboard_url": spec["dashboard_url"],
                    "validated": bool(profile.get("validated_at")),
                    "validated_at": profile.get("validated_at"),
                    "models": list(profile.get("models", [])),
                    "roles": dict(profile.get("roles", {})),
                    "active": provider == data.get("active_provider"),
                    "has_key": bool(profile.get("key_dpapi")),
                }
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "ready": self.ready,
            "active_provider": data.get("active_provider", ""),
            "profiles": profiles,
            "providers": [
                {
                    "provider": key,
                    **{k: v for k, v in spec.items() if k != "automatic_fallback_target"},
                }
                for key, spec in PROVIDERS.items()
            ],
            "fallback_policy": "ollama_cloud_only",
        }

    @property
    def ready(self) -> bool:
        data = self._load()
        active = data.get("active_provider")
        return bool(active and data["profiles"].get(active, {}).get("validated_at"))

    def validate_and_save(
        self,
        provider: str,
        api_key: str,
        *,
        roles: dict[str, str] | None = None,
        make_active: bool = True,
    ) -> dict:
        self._require_provider(provider)
        api_key = api_key.strip()
        if not api_key:
            raise ProviderHubError("API key required")
        models = self._list_models(provider, api_key)
        selected = self._validated_roles(provider, roles or self.preset(provider, models), models)
        self._test_conversation(provider, api_key, selected["conversation"])
        data = self._load()
        data["profiles"][provider] = {
            "key_dpapi": encrypt_str(api_key),
            "models": models,
            "roles": selected,
            "validated_at": time.time(),
        }
        if make_active:
            data["active_provider"] = provider
        self._save(data)
        self._record("provider_validated", provider, True)
        return self.public_profile(provider)

    def test(self, provider: str) -> dict:
        runtime = self.runtime(provider)
        models = self._list_models(provider, runtime.api_key)
        roles = self._validated_roles(provider, runtime.roles, models)
        self._test_conversation(provider, runtime.api_key, roles["conversation"])
        data = self._load()
        data["profiles"][provider]["models"] = models
        data["profiles"][provider]["roles"] = roles
        data["profiles"][provider]["validated_at"] = time.time()
        self._save(data)
        self._record("provider_tested", provider, True)
        return self.public_profile(provider)

    def set_roles(self, provider: str, roles: dict[str, str]) -> dict:
        data = self._load()
        profile = data["profiles"].get(provider)
        if not profile:
            raise ProviderHubError("provider profile not configured")
        profile["roles"] = self._validated_roles(provider, roles, profile.get("models", []))
        self._save(data)
        self._record("provider_roles_changed", provider, True)
        return self.public_profile(provider)

    def restore_preset(self, provider: str) -> dict:
        data = self._load()
        profile = data["profiles"].get(provider)
        if not profile:
            raise ProviderHubError("provider profile not configured")
        profile["roles"] = self.preset(provider, profile.get("models", []))
        self._save(data)
        self._record("provider_preset_restored", provider, True)
        return self.public_profile(provider)

    def set_active(self, provider: str) -> dict:
        data = self._load()
        profile = data["profiles"].get(provider)
        if not profile or not profile.get("validated_at"):
            raise ProviderHubError("provider must be validated before activation")
        data["active_provider"] = provider
        self._save(data)
        self._record("provider_activated", provider, True)
        return self.public_profile(provider)

    def revoke(self, provider: str) -> None:
        data = self._load()
        data["profiles"].pop(provider, None)
        if data.get("active_provider") == provider:
            data["active_provider"] = ""
        self._save(data)
        self._record("provider_revoked", provider, True)

    def runtime(self, provider: str | None = None) -> ProviderRuntime:
        data = self._load()
        selected = provider or data.get("active_provider")
        profile = data["profiles"].get(selected or "")
        if not selected or not profile or not profile.get("validated_at"):
            raise ProviderHubError("validated provider required")
        return ProviderRuntime(
            provider=selected,
            base_url=str(PROVIDERS[selected]["base_url"]),
            api_key=decrypt_str(profile["key_dpapi"]),
            roles=dict(profile["roles"]),
        )

    def ollama_fallback(self) -> ProviderRuntime | None:
        data = self._load()
        profile = data["profiles"].get("ollama_cloud")
        if not profile or not profile.get("validated_at"):
            return None
        return self.runtime("ollama_cloud")

    def public_profile(self, provider: str) -> dict:
        return next(
            (p for p in self.status()["profiles"] if p["provider"] == provider),
            {},
        )

    def preset(self, provider: str, models: list[str]) -> dict[str, str]:
        self._require_provider(provider)
        available = set(models)
        roles: dict[str, str] = {}
        for role, candidates in _PRESET_CANDIDATES[provider].items():
            selected = next((model for model in candidates if model in available), "")
            if selected:
                roles[role] = selected
        if "conversation" not in roles:
            # Nessun preset combacia: scegli un modello di CHAT, non il primo in
            # ordine alfabetico (poteva essere embedding/whisper/ecc → router rotto).
            chat_models = [m for m in models if not _NON_CHAT_ID.search(m)]
            if not chat_models:
                raise ProviderHubError("provider returned no chat-capable models")
            roles["conversation"] = chat_models[0]
            log.warning(
                "provider %s: nessun preset noto, conversation su '%s' "
                "(scelto tra %d modelli chat). Verifica il modello in Impostazioni.",
                provider, roles["conversation"], len(chat_models),
            )
            self._record("provider_preset_fallback", provider, True)
        roles.setdefault("reflection", roles["conversation"])
        roles.setdefault("tool_builder", roles["reflection"])
        return roles

    def migrate_legacy(self, provider: str, api_key: str, roles: dict[str, str]) -> bool:
        """Importa config legacy gia nota senza rete. Resta non validata."""
        if not api_key or provider not in PROVIDERS or self.public_profile(provider):
            return False
        data = self._load()
        data["profiles"][provider] = {
            "key_dpapi": encrypt_str(api_key),
            "models": sorted(set(filter(None, roles.values()))),
            "roles": {k: v for k, v in roles.items() if k in ROLE_NAMES and v},
            "validated_at": None,
        }
        self._save(data)
        self._record("provider_legacy_migrated", provider, True)
        return True

    def _list_models(self, provider: str, api_key: str) -> list[str]:
        response = self._request(
            "GET",
            f"{PROVIDERS[provider]['base_url']}/models",
            headers=self._headers(api_key),
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        models = sorted(
            {
                str(item.get("id", "")).strip()
                for item in payload.get("data", [])
                if isinstance(item, dict) and item.get("id")
            }
        )
        if not models:
            raise ProviderHubError("provider returned no models")
        return models

    def _test_conversation(self, provider: str, api_key: str, model: str) -> None:
        response = self._request(
            "POST",
            f"{PROVIDERS[provider]['base_url']}/chat/completions",
            headers=self._headers(api_key),
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply only with OK"}],
                "max_tokens": 8,
                "temperature": 0,
            },
            timeout=45,
        )
        response.raise_for_status()
        choices = response.json().get("choices") or []
        if not choices:
            raise ProviderHubError("provider conversation test returned no answer")

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _validated_roles(provider: str, roles: dict[str, str], models: list[str]) -> dict[str, str]:
        del provider
        if not isinstance(roles, dict):
            raise ProviderHubError("roles must be an object")
        available = set(models)
        selected = {
            role: str(model).strip()
            for role, model in roles.items()
            if role in ROLE_NAMES and str(model).strip()
        }
        if not selected.get("conversation"):
            raise ProviderHubError("conversation role required")
        unknown = sorted(set(selected.values()) - available)
        if unknown:
            raise ProviderHubError("models not available: " + ", ".join(unknown))
        return selected

    def _load(self) -> dict:
        if not self.path.exists():
            return {"schema_version": SCHEMA_VERSION, "active_provider": "", "profiles": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION or not isinstance(
            data.get("profiles"), dict
        ):
            raise ProviderHubError("invalid provider hub store")
        for provider in data["profiles"]:
            self._require_provider(provider)
        return data

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
        temp.replace(self.path)

    @staticmethod
    def _require_provider(provider: str) -> None:
        if provider not in PROVIDERS:
            raise ProviderHubError(f"unsupported provider: {provider}")

    def _record(self, event: str, provider: str, ok: bool) -> None:
        if self._audit:
            self._audit(event, {"provider": provider, "ok": ok})
