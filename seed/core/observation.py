"""D-OBS: observation lane READ-only (raccolta info utente, doc 16).

Osserva il PC in **sola lettura** (mai azione) per capire l'utente, estendendo
il watcher. Alimenta il modello cognitivo (CUK) e la memoria SOLO come
**candidate redatte a bassa confidenza** — mai fatti, mai diagnosi.

Vincoli non negoziabili (doc 16):

- READ-only assoluto: nessuna azione, click o scrittura;
- **consenso per-classe** (UI "cosa posso osservare"): default OFF per ogni
  classe; senza consenso il segnale viene scartato;
- **privacy gate** + redazione su ogni segnale: il lane riceve solo riferimenti
  gia' redatti/opachi, mai titoli/URL grezzi;
- **candidate-only**: al massimo un'ipotesi a bassa confidenza (claim_type
  `hypothesis`), mai un fatto; la correzione dell'utente prevale (regole CUK);
- **sensibile escluso** di default (salute/finanza/relazioni intime);
- **salienza prima del modello**: euristica deterministica decide cosa diventa
  candidate; il resto resta `remember_silently` o scartato;
- **audit aggregato**: classi/categorie/conteggi, mai contenuto personale grezzo;
- **revoca immediata** + purge dei derivati.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass

from .knowledge import UserClaim

log = logging.getLogger("seed.observation")

SCHEMA_VERSION = "seed.observation.v1"

# Classi osservabili, READ-only. Default OFF: il consenso si abilita per-classe.
OBSERVATION_CLASSES = frozenset({"foreground_app", "browser_tab", "process"})

# Categorie sensibili escluse di default (mai osservate/sintetizzate).
SENSITIVE_CATEGORIES = frozenset({"health", "finance", "intimate", "salute",
                                  "finanza", "relazioni"})

# Un ref redatto/opaco non deve contenere segreti evidenti.
_SECRET_LIKE = re.compile(r"[A-Za-z0-9_\-]{32,}")


class ObservationError(ValueError):
    pass


@dataclass(frozen=True)
class ObservationSignal:
    """Segnale gia' REDATTO dal watcher/privacy gate. Non contiene titoli o URL
    grezzi: solo classe, categoria generica e un riferimento redatto/opaco."""

    obs_class: str
    category: str
    redacted_ref: str
    salience: float
    sensitive: bool = False

    def validate(self) -> None:
        if self.obs_class not in OBSERVATION_CLASSES:
            raise ObservationError(f"classe non osservabile: {self.obs_class!r}")
        if not self.redacted_ref:
            raise ObservationError("redacted_ref mancante")
        if _SECRET_LIKE.search(self.redacted_ref):
            raise ObservationError("redacted_ref sospetto (possibile segreto/non redatto)")
        if not 0.0 <= float(self.salience) <= 1.0:
            raise ObservationError("salience fuori range [0,1]")


@dataclass(frozen=True)
class ObservationDecision:
    obs_class: str
    action: str                  # candidate | remember_silently | discard
    reasons: tuple[str, ...]


def decide_observation(signal: ObservationSignal, *, consent: frozenset[str],
                       sensitive_excluded: bool = True,
                       min_salience: float = 0.5) -> ObservationDecision:
    """Decisione deterministica. Default = scarta/silenzio: niente diventa
    candidate senza consenso esplicito e salienza sufficiente."""
    signal.validate()
    if signal.obs_class not in consent:
        return ObservationDecision(signal.obs_class, "discard",
                                   ("class_not_consented",))
    if sensitive_excluded and (signal.sensitive
                               or signal.category.lower() in SENSITIVE_CATEGORIES):
        return ObservationDecision(signal.obs_class, "discard",
                                   ("sensitive_excluded",))
    if signal.salience < min_salience:
        return ObservationDecision(signal.obs_class, "remember_silently",
                                   ("below_salience",))
    return ObservationDecision(signal.obs_class, "candidate", ("salient",))


class ObservationLane:
    """Processa segnali READ-only gia' redatti in candidate-ipotesi governate.
    Non osserva direttamente: riceve segnali (dal watcher) e li filtra. Nessuna
    azione, nessuna scrittura reale: solo candidate a bassa confidenza."""

    def __init__(self, memory, knowledge_store, *, enabled: bool = False,
                 sensitive_excluded: bool = True, min_salience: float = 0.5,
                 audit=None):
        self._memory = memory
        self._knowledge = knowledge_store
        self._enabled = bool(enabled)
        self._sensitive_excluded = bool(sensitive_excluded)
        self._min_salience = float(min_salience)
        self._audit = audit or (lambda kind, payload: None)

    # --- consenso per-classe (default OFF) ------------------------------
    def set_consent(self, obs_class: str, enabled: bool) -> None:
        if obs_class not in OBSERVATION_CLASSES:
            raise ObservationError(f"classe non osservabile: {obs_class!r}")
        self._memory.set_observation_consent(obs_class, bool(enabled))
        self._audit("observation_consent", {
            "schema_version": SCHEMA_VERSION, "obs_class": obs_class,
            "enabled": bool(enabled)})
        if not enabled:
            self._purge_class(obs_class)

    def consent(self) -> frozenset[str]:
        return frozenset(self._memory.observation_consent_classes())

    # --- ingestione segnali (READ-only) ---------------------------------
    def observe(self, signal: ObservationSignal) -> ObservationDecision:
        if not self._enabled:
            return ObservationDecision(signal.obs_class, "discard", ("lane_disabled",))
        decision = decide_observation(
            signal, consent=self.consent(),
            sensitive_excluded=self._sensitive_excluded,
            min_salience=self._min_salience)
        if decision.action == "candidate":
            self._record_candidate(signal)
        # Audit aggregato: classe/categoria/azione. Mai il redacted_ref.
        self._audit("observation_processed", {
            "schema_version": SCHEMA_VERSION,
            "obs_class": signal.obs_class,
            "category": signal.category,
            "action": decision.action,
            "write_actions": 0,
        })
        return decision

    def _record_candidate(self, signal: ObservationSignal) -> None:
        # Ipotesi a bassa confidenza: mai un fatto. La correzione utente prevale
        # (supersession in KnowledgeStore). Value = categoria generica, non grezzo.
        claim = UserClaim(
            claim_type="hypothesis",
            subject=f"observed:{signal.obs_class}",
            value=f"uso osservato categoria {signal.category}",
            confidence=min(0.45, signal.salience),
            confidence_source="inferred",
            scope="private",
            sensitivity="normal",
        )
        self._knowledge.record(claim.normalized())

    # --- revoca + purge -------------------------------------------------
    def revoke_all(self) -> int:
        for obs_class in OBSERVATION_CLASSES:
            self._memory.set_observation_consent(obs_class, False)
        purged = self._memory.purge_observation_candidates()
        self._audit("observation_revoked", {
            "schema_version": SCHEMA_VERSION, "purged": purged})
        return purged

    def _purge_class(self, obs_class: str) -> int:
        return self._memory.purge_observation_candidates(subject=f"observed:{obs_class}")

    # --- review aggregato -----------------------------------------------
    def review(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "enabled": self._enabled,
            "read_only": True,
            "write_actions": 0,
            "sensitive_excluded": self._sensitive_excluded,
            "min_salience": self._min_salience,
            "consented_classes": sorted(self.consent()),
            "observable_classes": sorted(OBSERVATION_CLASSES),
        }


class ObservationCollector:
    """Consent-first local collector. It never reads titles, URLs or content."""

    def __init__(self, lane: ObservationLane, *, poll_seconds: int = 15, audit=None):
        self.lane = lane
        self.poll_seconds = max(5, int(poll_seconds))
        self.audit = audit or (lambda kind, payload: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last: tuple[str, str] | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="seed-observation")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def collect_once(self) -> list[ObservationDecision]:
        consent = self.lane.consent()
        signals: list[ObservationSignal] = []
        if "foreground_app" in consent:
            from .watcher import _APP_CATEGORIES, _foreground_window
            exe, _title = _foreground_window()
            if exe:
                category = _APP_CATEGORIES.get(exe, "altro")
                signals.append(ObservationSignal(
                    "foreground_app", category, f"app:{category}", 0.65))
        if "process" in consent:
            try:
                import psutil
                categories = set()
                from .watcher import _APP_CATEGORIES
                for proc in psutil.process_iter(["name"]):
                    name = str(proc.info.get("name") or "").lower()
                    if name in _APP_CATEGORIES:
                        categories.add(_APP_CATEGORIES[name])
                signals.extend(ObservationSignal(
                    "process", category, f"process:{category}", 0.5)
                    for category in sorted(categories))
            except Exception:
                self.audit("observation_collector_error", {"collector": "process"})
        decisions = [self.lane.observe(signal) for signal in signals]
        self.audit("observation_collection", {
            "classes": sorted(consent), "signals": len(signals)})
        return decisions

    def _loop(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            self.collect_once()
