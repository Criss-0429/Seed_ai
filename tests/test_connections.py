"""P3 conversational connections preserve existing governance gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core.connections import CoreConnections  # noqa: E402
from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.skills import DelegationResult  # noqa: E402
from seed.core.tool_builder import ToolCandidate  # noqa: E402


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def chat(self, *_args, **_kwargs):
        return LLMResponse(text=json.dumps(self.replies.pop(0)))


class Cap:
    def __init__(self, capability_id, risk_class="safe", rollback=False):
        self.capability_id = capability_id
        self.risk_class = risk_class
        self.state = "active"
        self.manifest = {
            "description": capability_id,
            "rollback_supported": rollback,
        }


class Registry:
    def __init__(self, caps):
        self.caps = {cap.capability_id: cap for cap in caps}

    def active(self):
        return list(self.caps.values())

    def get(self, capability_id):
        return self.caps.get(capability_id)


class Builder:
    def __init__(self, root):
        self.root = root
        self.stage_calls = 0

    def registry_validate(self, manifest):
        required = {"capability_id", "description", "input_schema", "risk_class", "origin"}
        return [] if required <= set(manifest) else ["invalid"]

    def stage(self, manifest, code):
        self.stage_calls += 1
        candidate = self.root / manifest["capability_id"]
        candidate.mkdir(parents=True, exist_ok=True)
        (candidate / "REVIEW.json").write_text(json.dumps({
            "capability_id": manifest["capability_id"],
            "audit_passed": True,
            "test_passed": True,
            "violations": [],
        }), encoding="utf-8")
        return ToolCandidate(manifest["capability_id"], candidate, True, True, ())


class Subagent:
    allowed = frozenset({"read.status", "write.note"})

    def __init__(self):
        self.calls = 0

    def execute(self, request, arguments, *, owner_approved):
        self.calls += 1
        assert owner_approved is True
        return DelegationResult(True, {"n1": {"ok": True}}, None, "process")


def build(tmp_path, replies=(), caps=(), design_verdict="pass"):
    builder = Builder(tmp_path)
    subagent = Subagent()
    canary_calls = []
    connection = CoreConnections(
        tool_llm=FakeLLM(replies),
        registry=Registry(caps),
        tool_builder=builder,
        subagent=subagent,
        daemon_review=lambda: {"running": True, "os_service": False},
        advance_canary=lambda mutation_id: canary_calls.append(mutation_id) or [
            {"mutation_id": mutation_id, "action": "canary_started"}
        ],
        design_review=lambda _spec, _candidate: design_verdict,
    )
    return connection, builder, subagent, canary_calls


def test_heartbeat_is_visible_and_declares_no_os_service(tmp_path):
    connection, *_ = build(tmp_path)
    answer = connection.handle("stato heartbeat")
    assert '"running": true' in answer
    assert '"os_service": false' in answer


def test_tool_requires_scope_confirmation_before_generation(tmp_path):
    spec = {"capability_id": "echo.local", "description": "echo",
            "input_schema": {"value": "text"}, "risk_class": "safe",
            "needs_network": False}
    connection, builder, *_ = build(tmp_path, [spec, {"code": "print('{}')"}])
    preview = connection.handle("crea uno strumento che ripete un valore")
    assert builder.stage_calls == 0
    proposal_id = preview.split("`")[1]
    result = connection.handle(f"conferma tool {proposal_id}")
    assert builder.stage_calls == 1
    assert "Non installata" in result


def test_tool_design_review_fails_closed(tmp_path):
    spec = {"capability_id": "echo.local", "description": "echo",
            "input_schema": {}, "risk_class": "safe", "needs_network": False}
    connection, builder, *_ = build(
        tmp_path, [spec, {"code": "print('{}')"}], design_verdict="inconclusive")
    preview = connection.handle("crea uno strumento che risponde")
    proposal_id = preview.split("`")[1]
    result = connection.handle(f"conferma tool {proposal_id}")
    review = json.loads(
        (builder.root / "echo.local" / "REVIEW.json").read_text(encoding="utf-8"))
    assert "design review: inconclusive" in result
    assert review["design_review_passed"] is False
    assert review["installation_proposed"] is False


def test_plan_uses_allowlist_and_requires_confirmation(tmp_path):
    plan = {"nodes": [{"node_id": "n1", "capability_id": "read.status",
                       "depends_on": [], "arguments": {}}]}
    connection, _, subagent, _ = build(tmp_path, [plan], [Cap("read.status")])
    preview = connection.handle("pianifica controlla lo stato")
    assert subagent.calls == 0
    proposal_id = preview.split("`")[1]
    result = connection.handle(f"esegui piano {proposal_id}")
    assert subagent.calls == 1
    assert "verificato" in result


def test_plan_blocks_effect_without_verified_rollback(tmp_path):
    plan = {"nodes": [{"node_id": "n1", "capability_id": "write.note",
                       "depends_on": [], "arguments": {}}]}
    connection, _, subagent, _ = build(tmp_path, [plan], [Cap("write.note", "execute")])
    result = connection.handle("pianifica scrivi una nota")
    assert "adapter rollback verificato" in result
    assert subagent.calls == 0


def test_canary_requires_matching_confirmation_and_never_promotes(tmp_path):
    connection, *_, canary_calls = build(tmp_path)
    preview = connection.handle("avvia canary mutation-1")
    assert "non promuove" in preview
    assert canary_calls == []
    assert "non proposto" in connection.handle("conferma canary mutation-2")
    result = connection.handle("conferma canary mutation-1")
    assert canary_calls == ["mutation-1"]
    assert "Nessuna promotion automatica" in result
