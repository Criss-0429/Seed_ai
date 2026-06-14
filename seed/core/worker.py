"""D2: worker adapter READ-only dietro registry/permission/audit.

Prima attivazione del worker agentico (doc 16): delega capability-specifica,
SOLO letture allowlistate. Ogni azione ha un `ActionContract` tipizzato e passa
dal `PermissionBroker` + audit aggregato.

Confini D2 (owner-gated, doc 16):

- SOLO `side_effect_type == "read"`: nessuna scrittura, shell, file reale o
  worker esterno. `ActionContract.validate` rifiuta in registrazione qualunque
  azione non-read (read-only per costruzione);
- niente segreti al worker: riceve solo provider di stato AGGREGATO, mai
  config/key/memoria grezza; `run` rifiuta argomenti fuori schema o segreti;
- expected observation per ogni azione (active inference); rollback no-op per le
  letture;
- audit aggregato: action, esito, risk_class, dry_run, write_actions=0; mai
  output personale.

L'isolamento reale (container/subprocess ristretto) e' D3. La capability
WRITE_SAFE e' D4. Restano fuori scope, owner-gated.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from . import worker_sandbox

log = logging.getLogger("seed.worker")

SCHEMA_VERSION = "seed.worker.v1"

# D2: solo letture. Le risk class ammesse non chiedono prompt (vedi permissions)
# ma passano comunque dal broker per l'audit della decisione.
READ_ONLY_RISK_CLASSES = frozenset({"safe", "read_safe"})
READ_ONLY_SIDE_EFFECT = "read"

# Argomento sospetto: stringa lunga ad alta entropia (possibile key/segreto).
_SECRET_LIKE = re.compile(r"[A-Za-z0-9_\-]{32,}")


class WorkerError(ValueError):
    """Sollevata quando un'azione violerebbe i confini D2."""


@dataclass(frozen=True)
class ActionContract:
    """Contratto tipizzato di un'azione worker (doc 16). In D2 deve essere
    READ-only: `validate` impone gli invarianti."""

    name: str
    description: str
    input_schema: dict
    output_schema: dict
    risk_class: str
    allowed_scopes: tuple[str, ...]
    side_effect_type: str               # D2: solo "read"
    requires_approval: bool             # D2: False (letture safe)
    supports_dry_run: bool              # D2: True
    supports_rollback: bool
    observability_signal: str           # cosa osservare dopo l'azione

    def validate(self) -> None:
        if self.side_effect_type != READ_ONLY_SIDE_EFFECT:
            raise WorkerError(
                f"D2 e' READ-only: side_effect_type deve essere 'read', "
                f"non {self.side_effect_type!r} ({self.name})")
        if self.risk_class not in READ_ONLY_RISK_CLASSES:
            raise WorkerError(
                f"D2 ammette solo risk_class {sorted(READ_ONLY_RISK_CLASSES)}: "
                f"{self.risk_class!r} ({self.name})")
        if self.requires_approval:
            raise WorkerError(
                f"D2 read-only: nessuna azione richiede approval ({self.name})")
        if not self.supports_dry_run:
            raise WorkerError(
                f"D2: un'azione worker deve supportare dry-run ({self.name})")
        if not self.observability_signal:
            raise WorkerError(f"action contract senza observability_signal: {self.name}")


@dataclass(frozen=True)
class WorkerRequest:
    action: str
    arguments: dict = field(default_factory=dict)
    dry_run: bool = False


@dataclass(frozen=True)
class WorkerResult:
    action: str
    ok: bool
    output: dict
    observed: dict
    dry_run: bool
    audit: dict
    error: str | None = None


# handler: (arguments) -> dict di sola lettura, aggregato, senza segreti.
Handler = Callable[[dict], dict]


def _looks_secret(value) -> bool:
    return isinstance(value, str) and bool(_SECRET_LIKE.search(value))


class ReadOnlyWorker:
    """Adapter worker READ-only. Non riceve registry/sandbox/provider segreti:
    per costruzione non puo' scrivere, eseguire shell o leggere file reali."""

    def __init__(self, *, broker, audit=None, allowed_actions: tuple[str, ...] = ()):
        self._broker = broker
        self._audit = audit or (lambda kind, payload: None)
        self._allowed = set(allowed_actions)
        self._actions: dict[str, tuple[ActionContract, Handler]] = {}

    def register(self, contract: ActionContract, handler: Handler) -> None:
        contract.validate()
        self._actions[contract.name] = (contract, handler)

    def contracts(self) -> list[dict]:
        """Vista rivedibile dei contratti registrati (no segreti)."""
        out = []
        for contract, _ in self._actions.values():
            out.append({
                "schema_version": SCHEMA_VERSION,
                "name": contract.name,
                "description": contract.description,
                "risk_class": contract.risk_class,
                "side_effect_type": contract.side_effect_type,
                "requires_approval": contract.requires_approval,
                "supports_dry_run": contract.supports_dry_run,
                "supports_rollback": contract.supports_rollback,
                "observability_signal": contract.observability_signal,
                "allowlisted": contract.name in self._allowed,
            })
        return out

    def run(self, request: WorkerRequest) -> WorkerResult:
        entry = self._actions.get(request.action)
        if entry is None:
            return self._blocked(request, "azione worker non registrata")
        contract, handler = entry
        if request.action not in self._allowed:
            return self._blocked(request, "azione non allowlistata")

        try:
            contract.validate()                       # difesa: invarianti D2
            self._validate_arguments(contract, request.arguments)
        except WorkerError as exc:
            return self._blocked(request, str(exc))

        # D3: trust gate (hardening). Le letture passano senza approval; azioni
        # con effetti/destructive verrebbero bloccate o richiederebbero owner.
        gate = worker_sandbox.evaluate_trust_gate(contract, owner_approved=False)
        if not gate.allowed:
            return self._blocked(request,
                                 f"trust gate: {gate.blocked_reason}")

        # Permission broker: read_safe/safe non chiede prompt ma passa di qui.
        scope = contract.allowed_scopes[0] if contract.allowed_scopes else contract.risk_class
        if not self._broker.authorize(contract.name, contract.risk_class,
                                      str(scope), contract.description):
            return self._blocked(request, "permesso negato", denied=True)

        if request.dry_run:
            # Lettura in dry-run: nessun effetto, ritorna il piano.
            output = {"dry_run": True, "action": contract.name,
                      "observability_signal": contract.observability_signal}
            observed = {"planned": True}
            ok = True
        else:
            output = dict(handler(request.arguments) or {})
            observed = {"signal": contract.observability_signal, "observed": True}
            ok = True

        audit = self._audit_payload(contract, ok=ok, dry_run=request.dry_run)
        self._audit("worker_invoked", audit)
        return WorkerResult(contract.name, ok, output, observed,
                            request.dry_run, audit)

    # --- interni --------------------------------------------------------
    @staticmethod
    def _validate_arguments(contract: ActionContract, arguments: dict) -> None:
        unknown = set(arguments) - set(contract.input_schema)
        if unknown:
            raise WorkerError(f"argomenti fuori schema: {sorted(unknown)}")
        for key, value in arguments.items():
            if _looks_secret(value):
                raise WorkerError(f"argomento sospetto (possibile segreto): {key}")

    def _audit_payload(self, contract: ActionContract, *, ok: bool,
                       dry_run: bool) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "action": contract.name,
            "ok": ok,
            "risk_class": contract.risk_class,
            "side_effect_type": contract.side_effect_type,
            "dry_run": dry_run,
            "write_actions": 0,
        }

    def _blocked(self, request: WorkerRequest, reason: str,
                 denied: bool = False) -> WorkerResult:
        audit = {
            "schema_version": SCHEMA_VERSION,
            "action": request.action,
            "ok": False,
            "blocked": True,
            "denied": denied,
            "write_actions": 0,
        }
        self._audit("worker_blocked", audit)
        return WorkerResult(request.action, False, {}, {}, request.dry_run,
                            audit, error=reason)


def runtime_status_contract() -> ActionContract:
    """Prima azione worker D2: lettura dello stato runtime aggregato."""
    return ActionContract(
        name="worker.runtime_status",
        description="Riporta lo stato runtime aggregato (daemon, coda) in sola lettura.",
        input_schema={},
        output_schema={
            "daemon_running": "bool", "daemon_enabled": "bool",
            "queue_depth": "int", "tick_count": "int",
        },
        risk_class="read_safe",
        allowed_scopes=("runtime_status",),
        side_effect_type="read",
        requires_approval=False,
        supports_dry_run=True,
        supports_rollback=True,                 # no-op per una lettura
        observability_signal="runtime_status_readable",
    )


def build_runtime_status_worker(*, broker, status_provider: Callable[[], dict],
                                audit=None,
                                allowed_actions: tuple[str, ...] = (
                                    "worker.runtime_status",)) -> ReadOnlyWorker:
    """Costruisce il worker D2 con la sola azione READ-only di stato runtime.

    `status_provider` deve ritornare SOLO aggregati (nessun segreto, nessun dato
    personale): es. `BackgroundDaemon.review`."""
    worker = ReadOnlyWorker(broker=broker, audit=audit,
                            allowed_actions=allowed_actions)

    def _handler(_arguments: dict) -> dict:
        state = status_provider() or {}
        # Espone SOLO aggregati dal review del daemon: nessun topic_ref/testo.
        return {
            "daemon_running": bool(state.get("running")),
            "daemon_enabled": bool(state.get("enabled")),
            "queue_depth": int(state.get("queue_status_counts", {}).get("queued", 0)),
            "tick_count": int(state.get("tick_count", 0)),
            "supervised_process_only": True,
            "write_actions": 0,
        }

    worker.register(runtime_status_contract(), _handler)
    return worker
