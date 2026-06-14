"""D2 worker adapter READ-only: action contract, permission broker + audit,
dry-run, allowlist, niente segreti, ZERO scrittura."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core import worker as worker_mod  # noqa: E402
from seed.core.worker import (  # noqa: E402
    ActionContract, ReadOnlyWorker, WorkerError, WorkerRequest,
    build_runtime_status_worker, runtime_status_contract,
)
from seed.core.app import SeedApp  # noqa: E402


class _AllowBroker:
    """Broker che autorizza e registra la chiamata (read_safe non chiede prompt,
    ma il worker deve comunque passare di qui)."""

    def __init__(self):
        self.calls = []

    def authorize(self, capability_id, risk_class, scope, reason):
        self.calls.append((capability_id, risk_class, scope))
        return True


class _DenyBroker:
    def authorize(self, *a, **k):
        return False


def _status():
    return {"running": True, "enabled": True, "tick_count": 3,
            "queue_status_counts": {"queued": 2}}


# --- action contract ------------------------------------------------------
def test_runtime_status_contract_is_read_only():
    contract = runtime_status_contract()
    contract.validate()
    assert contract.side_effect_type == "read"
    assert contract.risk_class == "read_safe"
    assert contract.requires_approval is False
    assert contract.supports_dry_run is True


def test_contract_validate_rejects_write_side_effect():
    with pytest.raises(WorkerError):
        ActionContract(
            name="x", description="", input_schema={}, output_schema={},
            risk_class="read_safe", allowed_scopes=(), side_effect_type="write",
            requires_approval=False, supports_dry_run=True,
            supports_rollback=False, observability_signal="s").validate()


def test_contract_validate_rejects_non_read_risk_and_approval():
    with pytest.raises(WorkerError):
        ActionContract(
            name="x", description="", input_schema={}, output_schema={},
            risk_class="write", allowed_scopes=(), side_effect_type="read",
            requires_approval=False, supports_dry_run=True,
            supports_rollback=False, observability_signal="s").validate()
    with pytest.raises(WorkerError):
        ActionContract(
            name="x", description="", input_schema={}, output_schema={},
            risk_class="read_safe", allowed_scopes=(), side_effect_type="read",
            requires_approval=True, supports_dry_run=True,
            supports_rollback=False, observability_signal="s").validate()


def test_register_rejects_non_read_action():
    worker = ReadOnlyWorker(broker=_AllowBroker(), allowed_actions=("x",))
    bad = ActionContract(
        name="x", description="", input_schema={}, output_schema={},
        risk_class="read_safe", allowed_scopes=(), side_effect_type="execute",
        requires_approval=False, supports_dry_run=True,
        supports_rollback=False, observability_signal="s")
    with pytest.raises(WorkerError):
        worker.register(bad, lambda a: {})


# --- esecuzione READ-only -------------------------------------------------
def test_runtime_status_returns_aggregate_no_personal_data():
    broker = _AllowBroker()
    events = []
    worker = build_runtime_status_worker(
        broker=broker, status_provider=_status,
        audit=lambda k, p: events.append((k, p)))
    result = worker.run(WorkerRequest(action="worker.runtime_status"))
    assert result.ok
    assert result.output["daemon_running"] is True
    assert result.output["queue_depth"] == 2
    assert result.output["write_actions"] == 0
    assert broker.calls and broker.calls[0][1] == "read_safe"  # passa dal broker
    blob = json.dumps(result.output)
    assert "topic_ref" not in blob and "knowledge:" not in blob


def test_audit_is_aggregate_only():
    events = []
    worker = build_runtime_status_worker(
        broker=_AllowBroker(), status_provider=_status,
        audit=lambda k, p: events.append((k, p)))
    worker.run(WorkerRequest(action="worker.runtime_status"))
    kinds = [k for k, _ in events]
    assert "worker_invoked" in kinds
    payload = next(p for k, p in events if k == "worker_invoked")
    assert payload["write_actions"] == 0
    assert payload["side_effect_type"] == "read"
    # l'audit NON contiene l'output di stato
    assert "daemon_running" not in json.dumps(payload)


def test_dry_run_does_not_invoke_handler():
    called = {"n": 0}

    def provider():
        called["n"] += 1
        return _status()

    worker = build_runtime_status_worker(
        broker=_AllowBroker(), status_provider=provider)
    result = worker.run(WorkerRequest(action="worker.runtime_status", dry_run=True))
    assert result.ok and result.dry_run
    assert result.output["dry_run"] is True
    assert called["n"] == 0          # handler/provider mai chiamato in dry-run


# --- gate: allowlist, registrazione, permesso, segreti --------------------
def test_unregistered_action_blocked():
    worker = ReadOnlyWorker(broker=_AllowBroker(),
                            allowed_actions=("worker.runtime_status",))
    result = worker.run(WorkerRequest(action="worker.unknown"))
    assert not result.ok and result.audit["blocked"] is True


def test_non_allowlisted_action_blocked():
    worker = build_runtime_status_worker(
        broker=_AllowBroker(), status_provider=_status, allowed_actions=())
    result = worker.run(WorkerRequest(action="worker.runtime_status"))
    assert not result.ok
    assert "allowlist" in result.error


def test_permission_denied_blocks():
    worker = build_runtime_status_worker(
        broker=_DenyBroker(), status_provider=_status)
    result = worker.run(WorkerRequest(action="worker.runtime_status"))
    assert not result.ok and result.audit["denied"] is True


def test_arguments_out_of_schema_or_secret_rejected():
    worker = build_runtime_status_worker(
        broker=_AllowBroker(), status_provider=_status)
    # runtime_status non ha argomenti: qualunque chiave e' fuori schema
    out_of_schema = worker.run(
        WorkerRequest(action="worker.runtime_status", arguments={"foo": "bar"}))
    assert not out_of_schema.ok and "schema" in out_of_schema.error


# --- confini D2 (per costruzione) -----------------------------------------
def test_worker_module_has_no_execution_primitives():
    src = inspect.getsource(worker_mod)
    assert "import subprocess" not in src
    assert "import os" not in src
    assert "open(" not in src


# --- comando :worker ------------------------------------------------------
def test_worker_command_is_local_and_returns_status():
    class LocalOnly:
        @staticmethod
        def run_worker_status():
            return {"ok": True, "output": {"write_actions": 0}}

    result = json.loads(SeedApp.handle_message(LocalOnly(), ":worker"))
    assert result["ok"] is True
    assert result["output"]["write_actions"] == 0
