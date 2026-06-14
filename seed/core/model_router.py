"""S10 ModelRouter: separazione delle autorita per ruolo.

SEED non usa un solo modello per conversare, costruire tool e giudicare se quel
software rispetta SEED. Questi lavori hanno contesti, budget e autorita diversi
(doc `13_ModelRoles_Voice_Plan.md`).

Provider-neutral: un unico client OpenAI-compatible (stesso base_url+key); il
ruolo cambia SOLO il nome del modello per chiamata. Ogni chiamata registra
ruolo+modello+esito in audit aggregato — mai query, contenuto o segreto. Il nome
del modello e' un id pubblico, non un segreto.

S10.1 copre: config typed, router, audit per-call, fallback esplicito, migrazione
behavior-preserving di `conversation` e `tool_builder`. Reviewer (read-only,
schema-validato) e directive pack arrivano in S10.2/S10.3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from .llm import LLMClient, LLMResponse

log = logging.getLogger("seed.models")

ROLE_CONVERSATION = "conversation"
ROLE_TOOL_BUILDER = "tool_builder"
ROLE_DESIGN_REVIEWER = "design_reviewer"
ROLE_DESIGN_REVIEWER_FALLBACK = "design_reviewer_fallback"
ROLES = (
    ROLE_CONVERSATION,
    ROLE_TOOL_BUILDER,
    ROLE_DESIGN_REVIEWER,
    ROLE_DESIGN_REVIEWER_FALLBACK,
)

# Fallback espliciti per ruolo: nessuna escalation premium automatica.
_DEFAULT_FALLBACKS = {ROLE_DESIGN_REVIEWER: ROLE_DESIGN_REVIEWER_FALLBACK}


@dataclass
class RolePolicy:
    fail_closed_roles: tuple[str, ...] = (ROLE_DESIGN_REVIEWER,)
    record_model_per_call: bool = True
    allow_automatic_premium_escalation: bool = False
    fallbacks: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_FALLBACKS))


class BoundModel:
    """Vista client-compatibile legata a un ruolo: drop-in per i moduli che oggi
    ricevono un `LLMClient`. Espone `configured` e `chat(...)`, inietta il modello
    del ruolo e instrada l'audit. Se il chiamante passa `model=None`, vince il
    modello del ruolo (cosi i call site esistenti non devono conoscere i nomi)."""

    def __init__(self, router: "ModelRouter", role: str):
        self._router = router
        self._role = role

    @property
    def role(self) -> str:
        return self._role

    @property
    def configured(self) -> bool:
        return self._router.role_configured(self._role)

    def chat(self, messages: list[dict], **kw: Any) -> LLMResponse:
        return self._router.invoke(self._role, messages, **kw)


class ModelRouter:
    def __init__(
        self,
        client: LLMClient,
        roles: dict[str, str],
        policy: RolePolicy | None = None,
        audit: Callable[[str, dict], None] | None = None,
        *,
        provider: str = "",
        ollama_fallback_client: LLMClient | None = None,
        ollama_fallback_roles: dict[str, str] | None = None,
    ):
        self._client = client
        self._roles = dict(roles)
        self._policy = policy or RolePolicy()
        self._audit = audit
        self._provider = provider
        self._ollama_fallback_client = ollama_fallback_client
        self._ollama_fallback_roles = dict(ollama_fallback_roles or {})
        self.calls: dict[str, int] = {}      # contatori in-memory per ruolo
        self.fallbacks_used: int = 0

    # -- risoluzione --------------------------------------------------------
    def model_for(self, role: str) -> str:
        return self._roles.get(role, "")

    def role_configured(self, role: str) -> bool:
        """Credenziale presente E modello del ruolo configurato."""
        return self._client.has_key and bool(self.model_for(role))

    def bind(self, role: str) -> BoundModel:
        return BoundModel(self, role)

    # -- invocazione --------------------------------------------------------
    def invoke(self, role: str, messages: list[dict], *,
               model: str | None = None, **kw: Any) -> LLMResponse:
        chosen = model or self.model_for(role)
        if not chosen:
            raise RuntimeError(
                f"ModelRouter: nessun modello configurato per il ruolo '{role}'")
        try:
            resp = self._client.chat(messages, model=chosen, **kw)
            self._record(role, chosen, ok=True, fallback=False, resp=resp)
            return resp
        except Exception:
            fb_role = self._policy.fallbacks.get(role)
            fb_model = self.model_for(fb_role) if fb_role else ""
            if fb_model:
                try:
                    resp = self._client.chat(messages, model=fb_model, **kw)
                    self.fallbacks_used += 1
                    self._record(role, fb_model, ok=True, fallback=True, resp=resp)
                    return resp
                except Exception:
                    self._record(role, fb_model, ok=False, fallback=True)
            ollama_model = self._ollama_fallback_roles.get(role, "")
            if self._ollama_fallback_client is not None and ollama_model:
                try:
                    resp = self._ollama_fallback_client.chat(
                        messages, model=ollama_model, **kw)
                    self.fallbacks_used += 1
                    self._record(
                        role, ollama_model, ok=True, fallback=True, resp=resp,
                        provider="ollama_cloud")
                    return resp
                except Exception:
                    self._record(
                        role, ollama_model, ok=False, fallback=True,
                        provider="ollama_cloud")
            self._record(role, chosen, ok=False, fallback=False)
            raise

    # -- audit (aggregato, mai contenuto/segreto) ---------------------------
    def _record(self, role: str, model: str, *, ok: bool, fallback: bool,
                resp=None, provider: str | None = None) -> None:
        self.calls[role] = self.calls.get(role, 0) + 1
        if not (self._policy.record_model_per_call and self._audit):
            return
        # cost audit: solo conteggio token aggregato, mai contenuto.
        tokens = 0
        usage = getattr(resp, "usage", None)
        if isinstance(usage, dict):
            tokens = int(usage.get("total_tokens") or 0)
        payload = {
            "role": role, "model": model, "ok": ok,
            "fallback": fallback, "tokens": tokens,
        }
        active_provider = provider or self._provider
        if active_provider:
            payload["provider"] = active_provider
        self._audit("model_call", payload)


def resolve_roles(models_cfg, llm_cfg) -> dict[str, str]:
    """Risoluzione behavior-preserving (S10.1): se `models.roles` non specifica
    un ruolo, eredita dai due modelli legacy. `conversation` <- model_runtime,
    `tool_builder` <- model_reflection (o runtime se reflection vuoto, come oggi
    fa il fallback `model=... or None`). Reviewer restano vuoti finche' non
    configurati esplicitamente (S10.3 li abilita)."""
    roles = dict(getattr(models_cfg, "roles", {}) or {})
    roles.setdefault(ROLE_CONVERSATION, llm_cfg.model_runtime)
    roles.setdefault(
        ROLE_TOOL_BUILDER,
        llm_cfg.model_reflection or llm_cfg.model_runtime,
    )
    return roles
