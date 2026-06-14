"""D1: daemon agentico in background, SOLO a PC acceso e dentro SEED.

Il daemon vive esclusivamente nel processo SEED supervisionato (avviato da
`SeedApp.start_background`, fermato da `SeedApp.shutdown`). Non e' un servizio
OS, non ha auto-start ne always-on: a SEED chiuso non gira nulla.

Cosa fa in D1 e cosa NON fa (scope owner-gated, doc 16):

- heartbeat reviewable e aggregato (tick, profondita' coda, conteggi decisione);
- coda di proattivita' locale e persistente con cooldown, suppression e
  silenzio di default (la formula governata: parla solo se il valore atteso
  supera il costo di interruzione + privacy + trust);
- ZERO azioni agentiche di scrittura: il daemon decide soltanto se una
  candidate merita di essere mostrata all'owner; non invoca capability, shell,
  file reali, worker esterni o provider;
- niente dato personale, segreto o testo grezzo nella coda o nell'audit: le
  candidate referenziano la memoria con un `topic_ref` OPACO (es. `knowledge:12`),
  mai un valore o una frase.

Le fasi D2+ (worker adapter, observation lane, sandbox hardening, write-safe,
skills/delega e UI) restano fuori scope e owner-gated.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field

log = logging.getLogger("seed.daemon")

SCHEMA_VERSION = "seed.daemon.v1"

# Heartbeat e default conservativi. Il daemon e' in-process: questi valori NON
# creano alcun servizio OS o processo always-on.
DEFAULT_HEARTBEAT_SECONDS = 60.0
DEFAULT_COOLDOWN_SECONDS = 1800.0   # >=30 min tra due emit: niente raffica
DEFAULT_MIN_NET_VALUE = 0.0         # silenzio di default: deve SUPERARE il costo

# Categorie ammesse: etichette generiche e non personali. Una candidate non puo'
# trasportare testo libero: solo categoria + riferimento opaco.
ALLOWED_CATEGORIES = frozenset({
    "reminder", "followup", "suggestion", "summary_offer",
    "research_offer", "wellbeing_check",
})

# topic_ref deve essere OPACO: nome simbolico + id numerico opzionale
# (es. `knowledge:12`, `prediction:3`, `routine`). Mai spazi, mai frasi.
_OPAQUE_REF = re.compile(r"^[a-z][a-z0-9_]*(?::[0-9]+)?$")

# Soglia privacy: una candidate con costo privacy alto NON viene mai emessa
# autonomamente (resta suppressed, mai azione sensibile silenziosa).
_PRIVACY_HARD_GATE = 0.5

# Reason transitori: la candidate resta in coda e verra' rivalutata
# (cooldown che scade, categoria che l'owner riattiva). Gli altri reason sono
# terminali (silence/expire/privacy).
_TRANSIENT_REASONS = frozenset({"cooldown_active", "category_suppressed"})

_ACTION_TO_COUNT = {
    "emit": "emitted",
    "suppress": "suppressed",
    "silence": "silenced",
    "expire": "expired",
}


class DaemonError(ValueError):
    """Sollevata quando una candidate violerebbe i confini D1."""


def _clamp_cost(value: float, field_name: str) -> float:
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise DaemonError(f"{field_name} fuori range [0,1]: {value!r}")
    return value


@dataclass(frozen=True)
class ProactivityCandidate:
    """Una proposta di proattivita'. NON contiene testo personale: solo una
    categoria e un riferimento opaco alla memoria locale."""

    candidate_id: str
    category: str
    topic_ref: str
    expected_value: float
    interruption_cost: float
    privacy_cost: float
    trust_cost: float
    created_at: float
    expiry: float | None = None

    def validate(self) -> None:
        if self.category not in ALLOWED_CATEGORIES:
            raise DaemonError(f"categoria non ammessa: {self.category!r}")
        if not _OPAQUE_REF.fullmatch(self.topic_ref or ""):
            raise DaemonError(
                f"topic_ref non opaco (niente testo grezzo): {self.topic_ref!r}")
        _clamp_cost(self.expected_value, "expected_value")
        _clamp_cost(self.interruption_cost, "interruption_cost")
        _clamp_cost(self.privacy_cost, "privacy_cost")
        _clamp_cost(self.trust_cost, "trust_cost")


@dataclass(frozen=True)
class ProactivityDecision:
    candidate_id: str
    action: str                     # emit | suppress | silence | expire
    net_value: float
    reasons: tuple[str, ...]
    transient: bool = False         # True = la candidate resta in coda


def governed_net_value(candidate: ProactivityCandidate) -> float:
    """Formula harness (doc 16): parla solo se il valore atteso supera la somma
    dei costi di interruzione, privacy e trust."""
    net = candidate.expected_value - (
        candidate.interruption_cost
        + candidate.privacy_cost
        + candidate.trust_cost
    )
    return round(net, 6)


def decide_proactivity(
    candidate: ProactivityCandidate,
    *,
    now: float,
    last_emit_at: float | None = None,
    cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    suppressed_categories: tuple[str, ...] = (),
    min_net_value: float = DEFAULT_MIN_NET_VALUE,
) -> ProactivityDecision:
    """Decisione deterministica e spiegabile. Default = silenzio.

    Ordine dei gate: prima i verdetti TERMINALI (proprieta' intrinseche della
    candidate) — scadenza -> privacy hard gate -> silenzio di default — poi i
    verdetti TRANSIENTI (condizioni della coda) — suppression categoria ->
    cooldown — infine emit. I terminali vengono prima cosi' una candidate non
    saliente (sotto soglia) viene silenziata subito invece di restare in coda
    dietro un cooldown. Nessun ramo esegue un'azione: solo decisione rivedibile."""
    candidate.validate()
    net = governed_net_value(candidate)

    # --- verdetti terminali (proprieta' della candidate) ----------------
    if candidate.expiry is not None and now >= candidate.expiry:
        return ProactivityDecision(candidate.candidate_id, "expire", net,
                                   ("expired",))

    if candidate.privacy_cost >= _PRIVACY_HARD_GATE:
        # Mai proattivita' sensibile autonoma.
        return ProactivityDecision(candidate.candidate_id, "suppress", net,
                                   ("privacy_cost_high",))

    if net <= min_net_value:
        # Non saliente: il valore atteso non supera il costo. Silenzio.
        return ProactivityDecision(candidate.candidate_id, "silence", net,
                                   ("default_silence",))

    # --- verdetti transienti (condizioni della coda, candidate resta) ---
    if candidate.category in suppressed_categories:
        return ProactivityDecision(candidate.candidate_id, "suppress", net,
                                   ("category_suppressed",), transient=True)

    if last_emit_at is not None and (now - last_emit_at) < cooldown_seconds:
        return ProactivityDecision(candidate.candidate_id, "suppress", net,
                                   ("cooldown_active",), transient=True)

    return ProactivityDecision(candidate.candidate_id, "emit", net,
                               ("net_value_exceeds_cost",))


@dataclass
class HeartbeatStats:
    queue_depth: int = 0
    emitted: int = 0
    suppressed: int = 0
    silenced: int = 0
    expired: int = 0

    def record(self, action: str) -> None:
        key = _ACTION_TO_COUNT.get(action)
        if key is not None:
            setattr(self, key, getattr(self, key) + 1)


def build_heartbeat(*, tick: int, now: float, stats: HeartbeatStats,
                    alive: bool = True, can_run: bool = True) -> dict:
    """Battito aggregato e rivedibile. Dichiara esplicitamente i confini D1 e
    non contiene alcun dato personale: solo conteggi e flag."""
    return {
        "schema_version": SCHEMA_VERSION,
        "tick": int(tick),
        "at": round(float(now), 3),
        "alive": bool(alive),
        "can_run": bool(can_run),
        # Confini D1 resi espliciti nel battito stesso.
        "supervised_process_only": True,
        "os_service": False,
        "auto_start": False,
        "always_on": False,
        "write_actions": 0,
        "shell_access": False,
        "external_workers": False,
        "queue_depth": int(stats.queue_depth),
        "decisions": {
            "emitted": stats.emitted,
            "suppressed": stats.suppressed,
            "silenced": stats.silenced,
            "expired": stats.expired,
        },
    }


class BackgroundDaemon:
    """Loop di background supervisionato, in-process. Mirroring di `Scheduler`:
    thread daemon, `threading.Event` per lo stop, nessun servizio OS.

    Non riceve registry, broker, sandbox o provider: per costruzione non puo'
    eseguire azioni agentiche. Persiste battito e coda via `Memory`."""

    def __init__(
        self,
        memory,
        *,
        enabled: bool = True,
        heartbeat_seconds: float = DEFAULT_HEARTBEAT_SECONDS,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        min_net_value: float = DEFAULT_MIN_NET_VALUE,
        audit=None,
        clock=time.time,
        can_run=None,
    ):
        self._memory = memory
        self._enabled = bool(enabled)
        self._heartbeat_seconds = max(1.0, float(heartbeat_seconds))
        self._cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._min_net_value = float(min_net_value)
        self._audit = audit or (lambda kind, payload: None)
        self._clock = clock
        self._can_run = can_run or (lambda: True)
        self._suppressed_categories: set[str] = set()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    # --- lifecycle (legato al processo SEED) ----------------------------
    def start(self) -> None:
        if not self._enabled:
            self._audit("daemon_disabled", {"schema_version": SCHEMA_VERSION})
            log.info("daemon disabilitato da config")
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="seed-daemon")
        self._thread.start()
        self._audit("daemon_started", {"schema_version": SCHEMA_VERSION,
                                       "heartbeat_seconds": self._heartbeat_seconds})
        log.info("daemon avviato (heartbeat %.0fs)", self._heartbeat_seconds)

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2)
        self._audit("daemon_stopped", {"schema_version": SCHEMA_VERSION})

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # --- coda proattivita' ----------------------------------------------
    def enqueue(self, candidate: ProactivityCandidate) -> int:
        """Accoda una candidate gia' validata (categoria ammessa, ref opaco).
        Rifiuta qualunque cosa contenga testo grezzo o costi fuori range."""
        candidate.validate()
        return self._memory.enqueue_proactivity(
            candidate_id=candidate.candidate_id,
            category=candidate.category,
            topic_ref=candidate.topic_ref,
            net_value=governed_net_value(candidate),
            expected_value=candidate.expected_value,
            interruption_cost=candidate.interruption_cost,
            privacy_cost=candidate.privacy_cost,
            trust_cost=candidate.trust_cost,
            created_at=candidate.created_at,
            expiry=candidate.expiry,
        )

    def suppress_category(self, category: str, suppressed: bool = True) -> None:
        if category not in ALLOWED_CATEGORIES:
            raise DaemonError(f"categoria non ammessa: {category!r}")
        if suppressed:
            self._suppressed_categories.add(category)
        else:
            self._suppressed_categories.discard(category)

    # --- review (per owner/UI futura) -----------------------------------
    def review(self) -> dict:
        """Snapshot aggregato e rivedibile: stato daemon, conteggi coda e flag
        che dimostrano i confini D1. Nessun dato personale."""
        state = self._memory.daemon_state()
        return {
            "schema_version": SCHEMA_VERSION,
            "enabled": self._enabled,
            "running": self.running,
            "supervised_process_only": True,
            "os_service": False,
            "auto_start": False,
            "always_on": False,
            "write_actions": 0,
            "shell_access": False,
            "external_workers": False,
            "heartbeat_seconds": self._heartbeat_seconds,
            "cooldown_seconds": self._cooldown_seconds,
            "min_net_value": self._min_net_value,
            "suppressed_categories": sorted(self._suppressed_categories),
            "tick_count": state.get("tick_count", 0),
            "last_heartbeat_at": state.get("last_heartbeat_at"),
            "last_emit_at": state.get("last_emit_at"),
            "queue_status_counts": self._memory.proactivity_status_counts(),
        }

    # --- loop interno ----------------------------------------------------
    def _loop(self) -> None:
        # Primo tick immediato, poi attende heartbeat o stop.
        self._tick()
        while not self._stop.wait(self._heartbeat_seconds):
            self._tick()

    def _tick(self) -> None:
        with self._lock:
            try:
                self._tick_locked()
            except Exception:
                log.exception("daemon tick fallito")

    def _tick_locked(self) -> None:
        now = self._clock()
        state = self._memory.daemon_state()
        tick = int(state.get("tick_count", 0)) + 1
        can_run = bool(self._can_run())
        stats = HeartbeatStats(
            queue_depth=len(self._memory.proactivity_queue_items(status="queued")))

        if can_run:
            last_emit_at = state.get("last_emit_at")
            for row in self._memory.proactivity_queue_items(status="queued"):
                decision = decide_proactivity(
                    self._row_to_candidate(row),
                    now=now,
                    last_emit_at=last_emit_at,
                    cooldown_seconds=self._cooldown_seconds,
                    suppressed_categories=tuple(sorted(self._suppressed_categories)),
                    min_net_value=self._min_net_value,
                )
                stats.record(decision.action)
                self._apply_decision(row["id"], decision, now)
                if decision.action == "emit":
                    last_emit_at = now

        heartbeat = build_heartbeat(tick=tick, now=now, stats=stats,
                                    alive=True, can_run=can_run)
        self._memory.update_daemon_state(
            tick_count=tick,
            last_heartbeat_at=now,
            last_emit_at=last_emit_at if can_run else state.get("last_emit_at"),
        )
        # Audit ESCLUSIVAMENTE aggregato: solo conteggi e flag, mai topic_ref.
        self._audit("daemon_heartbeat", heartbeat)

    def _apply_decision(self, item_id: int,
                        decision: ProactivityDecision, now: float) -> None:
        if decision.transient:
            # Resta in coda: il cooldown scade, la categoria puo' riattivarsi.
            return
        status = {
            "emit": "emitted", "suppress": "suppressed",
            "silence": "silenced", "expire": "expired",
        }[decision.action]
        self._memory.set_proactivity_status(
            item_id, status,
            net_value=decision.net_value,
            reasons=list(decision.reasons),
            decided_at=now,
        )

    @staticmethod
    def _row_to_candidate(row: dict) -> ProactivityCandidate:
        return ProactivityCandidate(
            candidate_id=row["candidate_id"],
            category=row["category"],
            topic_ref=row["topic_ref"],
            expected_value=row["expected_value"],
            interruption_cost=row["interruption_cost"],
            privacy_cost=row["privacy_cost"],
            trust_cost=row["trust_cost"],
            created_at=row["created_at"],
            expiry=row["expiry"],
        )


def new_candidate_id() -> str:
    return uuid.uuid4().hex
