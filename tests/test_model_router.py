"""Test S10.1 ModelRouter: separazione ruoli, audit per-call, fallback esplicito.

Offline: nessun provider, nessuna rete. Un FakeClient registra il modello
ricevuto per chiamata e puo' fallire su modelli scelti per provare il fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.model_router import (  # noqa: E402
    ModelRouter,
    RolePolicy,
    resolve_roles,
)


class FakeClient:
    def __init__(self, has_key=True, fail_models=()):
        self.has_key = has_key
        self.fail_models = set(fail_models)
        self.calls: list[str] = []

    def chat(self, messages, *, model=None, **kw):
        self.calls.append(model)
        if model in self.fail_models:
            raise RuntimeError(f"boom {model}")
        return LLMResponse(text=f"ok:{model}")


class _Models:
    def __init__(self, roles):
        self.roles = roles


class _LLM:
    def __init__(self, runtime, reflection):
        self.model_runtime = runtime
        self.model_reflection = reflection


def _audit_sink():
    events: list[tuple[str, dict]] = []
    return events, lambda ev, payload: events.append((ev, payload))


# -- resolve_roles back-compat ---------------------------------------------

def test_resolve_roles_inherits_legacy_models():
    roles = resolve_roles(_Models({}), _LLM("runtime-x", "reflect-y"))
    assert roles["conversation"] == "runtime-x"
    assert roles["tool_builder"] == "reflect-y"


def test_resolve_roles_tool_builder_falls_back_to_runtime_when_reflection_empty():
    roles = resolve_roles(_Models({}), _LLM("runtime-x", ""))
    assert roles["tool_builder"] == "runtime-x"


def test_resolve_roles_explicit_roles_win():
    roles = resolve_roles(
        _Models({"conversation": "c", "design_reviewer": "rev"}),
        _LLM("runtime-x", "reflect-y"))
    assert roles["conversation"] == "c"          # esplicito vince
    assert roles["tool_builder"] == "reflect-y"  # mancante eredita
    assert roles["design_reviewer"] == "rev"


# -- invoke / bind ----------------------------------------------------------

def test_invoke_uses_role_model_and_records_audit():
    events, audit = _audit_sink()
    client = FakeClient()
    r = ModelRouter(client, {"conversation": "gemma", "tool_builder": "qwen"}, audit=audit)
    resp = r.invoke("conversation", [{"role": "user", "content": "ciao"}])
    assert resp.text == "ok:gemma"
    assert client.calls == ["gemma"]
    assert r.calls["conversation"] == 1
    assert events == [("model_call",
                       {"role": "conversation", "model": "gemma",
                        "ok": True, "fallback": False, "tokens": 0})]


def test_audit_never_contains_content_or_query():
    events, audit = _audit_sink()
    r = ModelRouter(FakeClient(), {"conversation": "gemma"}, audit=audit)
    r.invoke("conversation", [{"role": "user", "content": "segreto personale"}])
    payload = events[0][1]
    assert set(payload) == {"role", "model", "ok", "fallback", "tokens"}
    assert "segreto personale" not in str(payload)


def test_bound_model_injects_role_model_when_model_none():
    client = FakeClient()
    r = ModelRouter(client, {"conversation": "gemma", "tool_builder": "qwen"})
    conv = r.bind("conversation")
    builder = r.bind("tool_builder")
    conv.chat([], model=None, redacted=True)
    builder.chat([], redacted=True)
    assert client.calls == ["gemma", "qwen"]


def test_bound_model_explicit_model_overrides_role():
    client = FakeClient()
    r = ModelRouter(client, {"conversation": "gemma"})
    r.bind("conversation").chat([], model="override-model")
    assert client.calls == ["override-model"]


def test_role_configured_requires_key_and_model():
    r = ModelRouter(FakeClient(has_key=True), {"conversation": "gemma"})
    assert r.role_configured("conversation") is True
    assert r.role_configured("design_reviewer") is False  # modello non configurato
    r2 = ModelRouter(FakeClient(has_key=False), {"conversation": "gemma"})
    assert r2.role_configured("conversation") is False     # niente key


def test_invoke_raises_when_no_model_for_role():
    r = ModelRouter(FakeClient(), {"conversation": "gemma"})
    with pytest.raises(RuntimeError):
        r.invoke("design_reviewer", [])


# -- fallback esplicito -----------------------------------------------------

def test_fallback_used_when_primary_fails():
    events, audit = _audit_sink()
    client = FakeClient(fail_models=["gpt-oss"])
    r = ModelRouter(
        client,
        {"design_reviewer": "gpt-oss", "design_reviewer_fallback": "nemotron"},
        audit=audit)
    resp = r.invoke("design_reviewer", [])
    assert resp.text == "ok:nemotron"
    assert client.calls == ["gpt-oss", "nemotron"]   # primario poi fallback
    assert r.fallbacks_used == 1
    assert events[-1] == ("model_call",
                          {"role": "design_reviewer", "model": "nemotron",
                           "ok": True, "fallback": True, "tokens": 0})


def test_no_fallback_configured_raises_and_records_failure():
    events, audit = _audit_sink()
    client = FakeClient(fail_models=["gemma"])
    r = ModelRouter(client, {"conversation": "gemma"}, audit=audit)
    with pytest.raises(RuntimeError):
        r.invoke("conversation", [])
    assert events[-1] == ("model_call",
                          {"role": "conversation", "model": "gemma",
                           "ok": False, "fallback": False, "tokens": 0})


def test_record_disabled_emits_no_audit():
    events, audit = _audit_sink()
    policy = RolePolicy(record_model_per_call=False)
    r = ModelRouter(FakeClient(), {"conversation": "gemma"}, policy=policy, audit=audit)
    r.invoke("conversation", [])
    assert events == []
    assert r.calls["conversation"] == 1   # contatore interno resta
