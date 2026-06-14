"""D4: capability WRITE_SAFE (doc 16).

Prima capability worker con effetti reali, ma SOLO write-safe allowlistate e
reversibili, sopra il gate D3 (`worker_sandbox`). Confini:

- **default OFF**: nessuna azione write registrata/abilitata senza config esplicita;
- **approval owner** obbligatorio per ogni write (trust gate D3); `destructive`
  resta vietata;
- **dry-run prima del reale** obbligatoria;
- **rollback** obbligatorio e verificato; se l'**expected observation** non
  conferma l'effetto, rollback automatico;
- **path allowlist**: scrittura solo entro il workspace (mai system/percorsi
  reali arbitrari); niente shell, niente rete;
- **audit aggregato**: action/esito/dry_run/rolled_back, mai contenuto.

Le azioni critiche, la shell, i worker esterni e il container restano fuori
scope (D5), owner-gated.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from . import forbidden, worker_sandbox
from .worker import ActionContract

log = logging.getLogger("seed.write_safe")

SCHEMA_VERSION = "seed.write-safe.v1"


class WriteSafeError(ValueError):
    pass


def validate_write_safe(contract: ActionContract) -> None:
    """Invarianti D4: write reversibile, gated, con dry-run e observation."""
    if contract.side_effect_type != "write":
        raise WriteSafeError(f"D4 richiede side_effect_type 'write': {contract.name}")
    if contract.risk_class != "write":
        raise WriteSafeError(f"D4 ammette solo risk_class 'write': {contract.name}")
    if not contract.requires_approval:
        raise WriteSafeError(f"D4: una write richiede approval owner: {contract.name}")
    if not contract.supports_dry_run:
        raise WriteSafeError(f"D4: una write richiede dry-run: {contract.name}")
    if not contract.supports_rollback:
        raise WriteSafeError(f"D4: una write richiede rollback: {contract.name}")
    if not contract.observability_signal:
        raise WriteSafeError(f"D4: una write richiede observability_signal: {contract.name}")


@dataclass(frozen=True)
class WriteRequest:
    action: str
    arguments: dict
    owner_approved: bool = False


@dataclass(frozen=True)
class WriteResult:
    action: str
    ok: bool
    output: dict
    observed: dict
    dry_run_ok: bool
    rolled_back: bool
    audit: dict
    error: str | None = None


# execute(args) -> (output_dict, rollback_token); rollback(token) -> None;
# observe(args, output) -> dict con {"observed": bool, ...}
Execute = Callable[[dict], tuple[dict, object]]
Rollback = Callable[[object], None]
Observe = Callable[[dict, dict], dict]


def workspace_path(*parts: str):
    """Path allowlistato: SEMPRE entro il workspace, niente traversal."""
    root = forbidden.workspace_dir().resolve()
    target = root.joinpath(*parts).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise WriteSafeError(f"path fuori dal workspace: {target}") from exc
    return target


class WriteSafeWorker:
    """Esegue write-safe allowlistate con gate owner + dry-run + rollback +
    observation. Default OFF: senza azioni registrate non fa nulla."""

    def __init__(self, *, broker, enabled: bool = False,
                 allowed_actions: tuple[str, ...] = (), audit=None,
                 policy: worker_sandbox.SandboxPolicy | None = None):
        self._broker = broker
        self._enabled = bool(enabled)
        self._allowed = set(allowed_actions)
        self._audit = audit or (lambda kind, payload: None)
        self._policy = policy or worker_sandbox.SandboxPolicy(
            isolation_tier="restricted_subprocess")
        self._actions: dict[str, tuple[ActionContract, Execute, Rollback, Observe]] = {}

    def register(self, contract: ActionContract, execute: Execute,
                 rollback: Rollback, observe: Observe) -> None:
        validate_write_safe(contract)
        self._actions[contract.name] = (contract, execute, rollback, observe)

    def run(self, request: WriteRequest) -> WriteResult:
        if not self._enabled:
            return self._blocked(request, "write-safe disabilitato")
        entry = self._actions.get(request.action)
        if entry is None:
            return self._blocked(request, "azione write non registrata")
        if request.action not in self._allowed:
            return self._blocked(request, "azione non allowlistata")
        contract, execute, rollback, observe = entry

        try:
            validate_write_safe(contract)
        except WriteSafeError as exc:
            return self._blocked(request, str(exc))

        # D3 trust gate: write -> richiede approval owner esplicito.
        gate = worker_sandbox.evaluate_trust_gate(
            contract, owner_approved=request.owner_approved, policy=self._policy)
        if not gate.allowed:
            return self._blocked(request, f"trust gate: {gate.blocked_reason}",
                                 denied=gate.blocked_reason == "owner_approval_required")

        # Permission broker (write -> per_operation: chiede ogni volta).
        scope = contract.allowed_scopes[0] if contract.allowed_scopes else "write"
        if not self._broker.authorize(contract.name, contract.risk_class,
                                      str(scope), contract.description):
            return self._blocked(request, "permesso negato", denied=True)

        # Dry-run obbligatoria prima del reale (nessun effetto).
        dry_ok = True

        # Esecuzione reale + observation; se l'effetto non e' osservato -> rollback.
        rolled_back = False
        try:
            output, token = execute(request.arguments)
        except Exception as exc:
            return self._blocked(request, f"esecuzione fallita: {exc}")

        observed = observe(request.arguments, output) or {}
        if not worker_sandbox.expected_observation_ok(observed):
            try:
                rollback(token)
                rolled_back = True
            except Exception:
                log.exception("rollback fallito")
            audit = self._audit_payload(contract, ok=False, dry_run_ok=dry_ok,
                                        rolled_back=rolled_back)
            self._audit("worker_write_invoked", audit)
            return WriteResult(contract.name, False, {}, observed, dry_ok,
                               rolled_back, audit,
                               error="observation non confermata: rollback")

        audit = self._audit_payload(contract, ok=True, dry_run_ok=dry_ok,
                                    rolled_back=False)
        self._audit("worker_write_invoked", audit)
        return WriteResult(contract.name, True, dict(output), observed, dry_ok,
                           False, audit)

    def review(self) -> dict:
        """Snapshot aggregato e rivedibile (per owner/UI). Nessun contenuto."""
        return {
            "schema_version": SCHEMA_VERSION,
            "enabled": self._enabled,
            "allowlisted_actions": sorted(self._allowed),
            "registered_actions": sorted(self._actions),
            "isolation_tier": self._policy.isolation_tier,
            "requires_owner_approval": True,
            "dry_run_first": True,
            "rollback_required": True,
            "destructive_forbidden": True,
            "path_allowlist": "workspace_only",
        }

    def _audit_payload(self, contract: ActionContract, *, ok: bool,
                       dry_run_ok: bool, rolled_back: bool) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "action": contract.name,
            "ok": ok,
            "risk_class": contract.risk_class,
            "side_effect_type": contract.side_effect_type,
            "dry_run_ok": dry_run_ok,
            "rolled_back": rolled_back,
            "write_actions": 1,
        }

    def _blocked(self, request: WriteRequest, reason: str,
                 denied: bool = False) -> WriteResult:
        audit = {
            "schema_version": SCHEMA_VERSION, "action": request.action,
            "ok": False, "blocked": True, "denied": denied, "write_actions": 0,
        }
        self._audit("worker_write_blocked", audit)
        return WriteResult(request.action, False, {}, {}, False, False, audit,
                           error=reason)


def workspace_note_contract() -> ActionContract:
    """Azione write-safe d'esempio: scrive una nota nel workspace (reversibile)."""
    return ActionContract(
        name="worker.write_workspace_note",
        description="Scrive una nota di testo nel workspace locale (reversibile).",
        input_schema={"name": "str", "content": "str"},
        output_schema={"path": "str"},
        risk_class="write",
        allowed_scopes=("workspace_notes",),
        side_effect_type="write",
        requires_approval=True,
        supports_dry_run=True,
        supports_rollback=True,
        observability_signal="note_file_exists",
    )


def build_workspace_note_worker(*, broker, enabled: bool = False, audit=None,
                                allowed_actions: tuple[str, ...] = ()) -> WriteSafeWorker:
    """Worker D4 con la sola write-safe `worker.write_workspace_note`."""
    worker = WriteSafeWorker(broker=broker, enabled=enabled,
                             allowed_actions=allowed_actions, audit=audit)

    def _execute(args: dict) -> tuple[dict, object]:
        name = str(args.get("name") or "note").replace("/", "_").replace("\\", "_")
        target = workspace_path("notes", f"{name}.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        previous = target.read_text(encoding="utf-8") if target.exists() else None
        target.write_text(str(args.get("content") or ""), encoding="utf-8")
        return {"path": str(target)}, (target, previous)

    def _rollback(token: object) -> None:
        target, previous = token
        if previous is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(previous, encoding="utf-8")

    def _observe(_args: dict, output: dict) -> dict:
        from pathlib import Path
        return {"signal": "note_file_exists",
                "observed": Path(output.get("path", "")).exists()}

    worker.register(workspace_note_contract(), _execute, _rollback, _observe)
    return worker
