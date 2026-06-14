"""Memoria locale SQLite: episodi, fatti (bi-temporali), preferenze, pii_map,
grant permessi, statistiche capability, alias del router, eventi telemetria.

Tutto in %LOCALAPPDATA%/SEED/data/seed.db — non lascia mai il PC.
La pii_map e' cifrata at rest con DPAPI su Windows (chiave legata all'account).
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import time
from pathlib import Path

from . import forbidden

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    source TEXT NOT NULL,           -- chat | watcher | system | survey
    category TEXT,
    payload TEXT NOT NULL           -- JSON (gia' redatto se contiene testo libero)
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    created_at REAL NOT NULL,
    superseded_at REAL,             -- bi-temporalita': si supera, non si cancella
    statement TEXT NOT NULL,
    confidence REAL NOT NULL,
    provenance TEXT NOT NULL        -- JSON: episode ids
);
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY,
    created_at REAL NOT NULL,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    explicit INTEGER NOT NULL DEFAULT 1   -- 1 = detto dall'utente: vince sempre
);
CREATE TABLE IF NOT EXISTS pii_map (
    placeholder TEXT PRIMARY KEY,
    value_enc TEXT NOT NULL,        -- DPAPI/base64
    label TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS grants (
    id INTEGER PRIMARY KEY,
    capability_id TEXT NOT NULL,
    scope TEXT NOT NULL,            -- es. path cartella, "network", nome app
    decision TEXT NOT NULL,         -- allow | deny
    remembered INTEGER NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS capability_stats (
    capability_id TEXT PRIMARY KEY,
    invocations INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    failures INTEGER NOT NULL DEFAULT 0,
    last_used REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aliases (
    normalized TEXT PRIMARY KEY,    -- comando normalizzato
    intent TEXT NOT NULL,           -- intent del router
    args TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS onboarding_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS voice_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    consent INTEGER NOT NULL DEFAULT 0,    -- S11: consenso voce separato
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS onboarding_items (
    id INTEGER PRIMARY KEY,
    created_at REAL NOT NULL,
    kind TEXT NOT NULL,
    statement TEXT NOT NULL,
    confidence REAL NOT NULL,
    explicit INTEGER NOT NULL,
    provenance TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY,
    created_at REAL NOT NULL,
    valid_from REAL NOT NULL,
    valid_to REAL,                       -- bi-temporale: NULL = valido ora
    superseded_at REAL,                  -- quando sostituito da un claim piu' nuovo
    claim_type TEXT NOT NULL,            -- fact|state|routine|pattern|preference|relation|exception|hypothesis|boundary
    subject TEXT NOT NULL,               -- slot normalizzato (chiave di supersession con claim_type)
    value TEXT NOT NULL,
    confidence REAL NOT NULL,
    confidence_source TEXT NOT NULL,     -- explicit | inferred
    scope TEXT NOT NULL DEFAULT 'private',
    sensitivity TEXT NOT NULL DEFAULT 'normal',  -- normal | sensitive
    provenance TEXT NOT NULL,            -- JSON: episode ids
    lifecycle_state TEXT NOT NULL,       -- candidate | active | superseded | rejected
    review_state TEXT NOT NULL DEFAULT 'unreviewed'  -- unreviewed | confirmed | corrected
);
CREATE TABLE IF NOT EXISTS knowledge_edges (
    id INTEGER PRIMARY KEY,
    created_at REAL NOT NULL,
    source_id INTEGER NOT NULL,          -- knowledge.id
    target_id INTEGER NOT NULL,          -- knowledge.id
    edge_type TEXT NOT NULL,             -- supports|contradicts|supersedes|attenuates|activates|inhibits|predicts|explains|co_occurs|depends_on
    weight REAL NOT NULL DEFAULT 1.0,
    confidence REAL NOT NULL DEFAULT 0.6,
    valid_from REAL NOT NULL,
    valid_to REAL,
    provenance TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS living_profile_versions (
    id INTEGER PRIMARY KEY,
    version INTEGER UNIQUE NOT NULL,
    generated_at REAL NOT NULL,
    sections TEXT NOT NULL,               -- JSON, derivato rigenerabile
    source_claim_ids TEXT NOT NULL,       -- JSON
    delta TEXT NOT NULL,                  -- JSON: added/removed claim ids
    confidence REAL NOT NULL,
    review_state TEXT NOT NULL DEFAULT 'candidate' -- candidate|approved|rejected
);
CREATE TABLE IF NOT EXISTS counterpoint_versions (
    id INTEGER PRIMARY KEY,
    version INTEGER UNIQUE NOT NULL,
    generated_at REAL NOT NULL,
    fragments TEXT NOT NULL,              -- JSON, dubbi separati dai fatti
    source_claim_ids TEXT NOT NULL,       -- JSON
    confidence REAL NOT NULL,
    review_state TEXT NOT NULL DEFAULT 'candidate'
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY,
    created_at REAL NOT NULL,
    source_claim_id INTEGER NOT NULL,         -- knowledge.id del pattern
    predicted_event TEXT NOT NULL,
    probability REAL NOT NULL,
    horizon_days INTEGER NOT NULL,
    observation_window_days INTEGER NOT NULL,
    outcome TEXT NOT NULL DEFAULT 'open',      -- open | confirmed | refuted
    resolved_at REAL
);
CREATE TABLE IF NOT EXISTS salience_decisions (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    item_ref TEXT NOT NULL,                -- knowledge:<id> | fact:<id> | counterpoint:<n>
    action TEXT NOT NULL,                  -- use_context | remember_silently
    score REAL NOT NULL,
    reasons TEXT NOT NULL,                 -- JSON, mai query/valore personale
    factors TEXT NOT NULL                  -- JSON numerico, aggregate-safe
);
CREATE TABLE IF NOT EXISTS personality_decisions (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    mode TEXT NOT NULL,
    explicit_mode INTEGER NOT NULL,
    counterpoint_required INTEGER NOT NULL,
    reasons TEXT NOT NULL,
    preference_keys TEXT NOT NULL,
    violations TEXT NOT NULL DEFAULT '[]',
    repaired INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS proactivity_queue (
    id INTEGER PRIMARY KEY,
    candidate_id TEXT UNIQUE NOT NULL,
    created_at REAL NOT NULL,
    category TEXT NOT NULL,                 -- etichetta generica, mai personale
    topic_ref TEXT NOT NULL,               -- OPACO (es. knowledge:12), mai testo grezzo
    net_value REAL NOT NULL,
    expected_value REAL NOT NULL,
    interruption_cost REAL NOT NULL,
    privacy_cost REAL NOT NULL,
    trust_cost REAL NOT NULL,
    expiry REAL,
    status TEXT NOT NULL DEFAULT 'queued', -- queued|emitted|suppressed|silenced|expired
    decided_at REAL,
    reasons TEXT NOT NULL DEFAULT '[]'      -- JSON, aggregate-safe (stringhe fisse)
);
CREATE TABLE IF NOT EXISTS daemon_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    tick_count INTEGER NOT NULL DEFAULT 0,
    last_heartbeat_at REAL,
    last_emit_at REAL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS observation_consent (
    obs_class TEXT PRIMARY KEY,            -- foreground_app|browser_tab|process
    enabled INTEGER NOT NULL DEFAULT 0,    -- D-OBS: default OFF per-classe
    updated_at REAL NOT NULL
);
"""


def _dpapi_encrypt(data: bytes) -> bytes:
    if os.name == "nt":
        try:
            import ctypes
            import ctypes.wintypes as wt

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

            blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_char)))
            blob_out = DATA_BLOB()
            if ctypes.windll.crypt32.CryptProtectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
                out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return out
        except Exception:
            pass
    return data  # non-Windows (dev): passthrough


def _dpapi_decrypt(data: bytes) -> bytes:
    if os.name == "nt":
        try:
            import ctypes
            import ctypes.wintypes as wt

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

            blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_char)))
            blob_out = DATA_BLOB()
            if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
                out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return out
        except Exception:
            pass
    return data


class Memory:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or (forbidden.seed_data_dir() / "data" / "seed.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Connessione condivisa tra thread (main + scheduler + daemon): autocommit
        # (`isolation_level=None`) cosi' non esiste uno stato di transazione globale
        # che un commit concorrente possa azzerare ("cannot commit - no transaction
        # is active"). SQLite serializza le scritture col suo mutex; `busy_timeout`
        # attende invece di fallire. Le scritture multi-statement che richiedono
        # atomicita' usano BEGIN/COMMIT espliciti (vedi `clear_onboarding`).
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False,
                                     isolation_level=None)
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.executescript(_SCHEMA)

    # --- episodes -----------------------------------------------------
    def add_episode(self, source: str, payload: dict, category: str | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO episodes (ts, source, category, payload) VALUES (?,?,?,?)",
            (time.time(), source, category, json.dumps(payload, ensure_ascii=False)))
        self._conn.commit()
        return cur.lastrowid

    def episodes_since(self, ts: float) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, ts, source, category, payload FROM episodes WHERE ts >= ? ORDER BY ts", (ts,))
        return [{"id": r[0], "ts": r[1], "source": r[2], "category": r[3],
                 "payload": json.loads(r[4])} for r in rows]

    def recent_chat(self, limit: int = 20) -> list[dict]:
        """M1: ultimi turni di chat in ordine cronologico, come messaggi
        {role, content}. Esclude onboarding. Serve a ricaricare la cronologia
        conversazionale tra una sessione e l'altra (oggi `_history` e' in RAM)."""
        return [
            {"role": item["role"], "content": item["content"]}
            for item in self.recent_chat_records(limit)
        ]

    def recent_chat_records(self, limit: int = 20) -> list[dict]:
        """Come `recent_chat`, ma conserva id/ts per provenance M2/K2."""
        rows = self._conn.execute(
            "SELECT id, ts, payload FROM episodes WHERE source='chat' AND category='chat' "
            "ORDER BY ts DESC, id DESC LIMIT ?", (max(0, int(limit)),))
        out: list[dict] = []
        for episode_id, ts, payload in rows:
            p = json.loads(payload)
            role, text = p.get("role"), p.get("text")
            if role in ("user", "assistant") and isinstance(text, str):
                out.append({
                    "id": episode_id, "ts": ts, "role": role, "content": text})
        out.reverse()
        return out

    def find_user_chat_episode_containing(self, text: str) -> int | None:
        """Backfill provenance legacy: trova il messaggio utente piu' recente
        che contiene letteralmente il valore. Nessuna inferenza o fuzzy match."""
        needle = text.strip().lower()
        if not needle:
            return None
        rows = self._conn.execute(
            "SELECT id, payload FROM episodes WHERE source='chat' AND category='chat' "
            "ORDER BY ts DESC, id DESC")
        for episode_id, payload in rows:
            p = json.loads(payload)
            if p.get("role") != "user":
                continue
            value = p.get("text")
            if isinstance(value, str) and needle in value.lower():
                return episode_id
        return None

    # --- facts ----------------------------------------------------------
    def add_fact(self, statement: str, confidence: float, provenance: list[int]) -> int:
        cur = self._conn.execute(
            "INSERT INTO facts (created_at, statement, confidence, provenance) VALUES (?,?,?,?)",
            (time.time(), statement, confidence, json.dumps(provenance)))
        self._conn.commit()
        return cur.lastrowid

    def supersede_fact(self, fact_id: int) -> None:
        self._conn.execute("UPDATE facts SET superseded_at = ? WHERE id = ?", (time.time(), fact_id))
        self._conn.commit()

    def active_facts(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, statement, confidence FROM facts WHERE superseded_at IS NULL")
        return [{"id": r[0], "statement": r[1], "confidence": r[2]} for r in rows]

    # --- knowledge (M2: claim tipizzati bi-temporali) -------------------
    def add_knowledge(self, *, claim_type: str, subject: str, value: str,
                      confidence: float, confidence_source: str,
                      provenance: list[int], lifecycle_state: str,
                      scope: str = "private", sensitivity: str = "normal",
                      review_state: str = "unreviewed",
                      valid_from: float | None = None) -> int:
        now = time.time()
        cur = self._conn.execute(
            "INSERT INTO knowledge (created_at, valid_from, claim_type, subject, "
            "value, confidence, confidence_source, scope, sensitivity, provenance, "
            "lifecycle_state, review_state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (now, valid_from if valid_from is not None else now, claim_type,
             subject, value, float(confidence), confidence_source, scope,
             sensitivity, json.dumps(provenance), lifecycle_state, review_state))
        self._conn.commit()
        return cur.lastrowid

    def _knowledge_row(self, r) -> dict:
        return {"id": r[0], "created_at": r[1], "valid_from": r[2], "valid_to": r[3],
                "superseded_at": r[4], "claim_type": r[5], "subject": r[6],
                "value": r[7], "confidence": r[8], "confidence_source": r[9],
                "scope": r[10], "sensitivity": r[11], "provenance": json.loads(r[12]),
                "lifecycle_state": r[13], "review_state": r[14]}

    _K_COLS = ("id, created_at, valid_from, valid_to, superseded_at, claim_type, "
               "subject, value, confidence, confidence_source, scope, sensitivity, "
               "provenance, lifecycle_state, review_state")

    def active_knowledge(self, claim_type: str | None = None) -> list[dict]:
        q = (f"SELECT {self._K_COLS} FROM knowledge WHERE lifecycle_state='active' "
             "AND superseded_at IS NULL")
        params: tuple = ()
        if claim_type is not None:
            q += " AND claim_type=?"
            params = (claim_type,)
        q += " ORDER BY created_at DESC"
        return [self._knowledge_row(r) for r in self._conn.execute(q, params)]

    def knowledge_active_by_key(self, claim_type: str, subject: str) -> dict | None:
        row = self._conn.execute(
            f"SELECT {self._K_COLS} FROM knowledge WHERE claim_type=? AND subject=? "
            "AND lifecycle_state IN ('active','candidate') AND superseded_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1", (claim_type, subject)).fetchone()
        return self._knowledge_row(row) if row else None

    def supersede_knowledge(self, knowledge_id: int) -> None:
        now = time.time()
        self._conn.execute(
            "UPDATE knowledge SET superseded_at=?, valid_to=?, lifecycle_state='superseded' "
            "WHERE id=?", (now, now, knowledge_id))
        self._conn.commit()

    def set_knowledge_review(self, knowledge_id: int, review_state: str) -> None:
        self._conn.execute("UPDATE knowledge SET review_state=? WHERE id=?",
                           (review_state, knowledge_id))
        self._conn.commit()

    def set_knowledge_provenance(self, knowledge_id: int,
                                 provenance: list[int]) -> None:
        self._conn.execute(
            "UPDATE knowledge SET provenance=? WHERE id=?",
            (json.dumps(provenance), int(knowledge_id)))
        self._conn.commit()

    def all_knowledge(self) -> list[dict]:
        return [self._knowledge_row(r) for r in self._conn.execute(
            f"SELECT {self._K_COLS} FROM knowledge ORDER BY created_at")]

    # --- knowledge edges (M3: collegamenti semantici tipati) ------------
    def add_edge(self, *, source_id: int, target_id: int, edge_type: str,
                 weight: float = 1.0, confidence: float = 0.6,
                 provenance: list[int] | None = None) -> int:
        now = time.time()
        cur = self._conn.execute(
            "INSERT INTO knowledge_edges (created_at, source_id, target_id, "
            "edge_type, weight, confidence, valid_from, provenance) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (now, source_id, target_id, edge_type, float(weight),
             float(confidence), now, json.dumps(provenance or [])))
        self._conn.commit()
        return cur.lastrowid

    def _edge_row(self, r) -> dict:
        return {"id": r[0], "created_at": r[1], "source_id": r[2],
                "target_id": r[3], "edge_type": r[4], "weight": r[5],
                "confidence": r[6], "valid_from": r[7], "valid_to": r[8],
                "provenance": json.loads(r[9])}

    _E_COLS = ("id, created_at, source_id, target_id, edge_type, weight, "
               "confidence, valid_from, valid_to, provenance")

    def all_edges(self) -> list[dict]:
        return [self._edge_row(r) for r in self._conn.execute(
            f"SELECT {self._E_COLS} FROM knowledge_edges WHERE valid_to IS NULL")]

    def edges_for(self, node_id: int) -> list[dict]:
        return [self._edge_row(r) for r in self._conn.execute(
            f"SELECT {self._E_COLS} FROM knowledge_edges WHERE valid_to IS NULL "
            "AND (source_id=? OR target_id=?)", (node_id, node_id))]

    def close_edges_for(self, node_id: int, *, exclude_type: str | None = None) -> int:
        """K4 stale cascade: chiude (valid_to) gli edge attivi del nodo superato,
        cosi' i derivati vecchi non vengono piu' usati. Mantiene gli edge
        `exclude_type` (es. 'supersedes', che e' la storia)."""
        now = time.time()
        q = ("UPDATE knowledge_edges SET valid_to=? WHERE valid_to IS NULL "
             "AND (source_id=? OR target_id=?)")
        params: list = [now, node_id, node_id]
        if exclude_type is not None:
            q += " AND edge_type != ?"
            params.append(exclude_type)
        cur = self._conn.execute(q, params)
        self._conn.commit()
        return cur.rowcount

    def set_knowledge_confidence(self, knowledge_id: int, confidence: float) -> None:
        self._conn.execute("UPDATE knowledge SET confidence=? WHERE id=?",
                           (max(0.0, min(1.0, float(confidence))), knowledge_id))
        self._conn.commit()

    # --- predictions (K4: predict-calibrate) ----------------------------
    def add_prediction(self, *, source_claim_id: int, predicted_event: str,
                       probability: float, horizon_days: int,
                       observation_window_days: int) -> int:
        cur = self._conn.execute(
            "INSERT INTO predictions (created_at, source_claim_id, predicted_event, "
            "probability, horizon_days, observation_window_days) VALUES (?,?,?,?,?,?)",
            (time.time(), source_claim_id, predicted_event, float(probability),
             int(horizon_days), int(observation_window_days)))
        self._conn.commit()
        return cur.lastrowid

    def _prediction_row(self, r) -> dict:
        return {"id": r[0], "created_at": r[1], "source_claim_id": r[2],
                "predicted_event": r[3], "probability": r[4], "horizon_days": r[5],
                "observation_window_days": r[6], "outcome": r[7], "resolved_at": r[8]}

    _P_COLS = ("id, created_at, source_claim_id, predicted_event, probability, "
               "horizon_days, observation_window_days, outcome, resolved_at")

    def all_predictions(self) -> list[dict]:
        return [self._prediction_row(r) for r in self._conn.execute(
            f"SELECT {self._P_COLS} FROM predictions ORDER BY created_at")]

    def open_predictions(self) -> list[dict]:
        return [self._prediction_row(r) for r in self._conn.execute(
            f"SELECT {self._P_COLS} FROM predictions WHERE outcome='open'")]

    def has_open_prediction(self, source_claim_id: int) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM predictions WHERE source_claim_id=? AND outcome='open' LIMIT 1",
            (source_claim_id,)).fetchone() is not None

    def resolve_prediction(self, prediction_id: int, outcome: str) -> None:
        self._conn.execute(
            "UPDATE predictions SET outcome=?, resolved_at=? WHERE id=?",
            (outcome, time.time(), prediction_id))
        self._conn.commit()

    # --- K2: living profile + counterpoint versionati -------------------
    def add_living_profile(self, *, sections: dict, source_claim_ids: list[int],
                           delta: dict, confidence: float) -> int:
        version = self._next_version("living_profile_versions")
        cur = self._conn.execute(
            "INSERT INTO living_profile_versions "
            "(version, generated_at, sections, source_claim_ids, delta, confidence) "
            "VALUES (?,?,?,?,?,?)",
            (version, time.time(), json.dumps(sections, ensure_ascii=False),
             json.dumps(source_claim_ids), json.dumps(delta), float(confidence)))
        self._conn.commit()
        return cur.lastrowid

    def living_profiles(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, version, generated_at, sections, source_claim_ids, delta, "
            "confidence, review_state FROM living_profile_versions ORDER BY version")
        return [{
            "id": r[0], "version": r[1], "generated_at": r[2],
            "sections": json.loads(r[3]), "source_claim_ids": json.loads(r[4]),
            "delta": json.loads(r[5]), "confidence": r[6], "review_state": r[7],
        } for r in rows]

    def latest_living_profile(self, review_state: str | None = None) -> dict | None:
        rows = self.living_profiles()
        if review_state is not None:
            rows = [r for r in rows if r["review_state"] == review_state]
        return rows[-1] if rows else None

    def set_living_profile_review(self, version: int, review_state: str) -> None:
        self._set_derived_review("living_profile_versions", version, review_state)

    def add_counterpoint(self, *, fragments: list[dict],
                         source_claim_ids: list[int], confidence: float) -> int:
        version = self._next_version("counterpoint_versions")
        cur = self._conn.execute(
            "INSERT INTO counterpoint_versions "
            "(version, generated_at, fragments, source_claim_ids, confidence) "
            "VALUES (?,?,?,?,?)",
            (version, time.time(), json.dumps(fragments, ensure_ascii=False),
             json.dumps(source_claim_ids), float(confidence)))
        self._conn.commit()
        return cur.lastrowid

    def counterpoints(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, version, generated_at, fragments, source_claim_ids, "
            "confidence, review_state FROM counterpoint_versions ORDER BY version")
        return [{
            "id": r[0], "version": r[1], "generated_at": r[2],
            "fragments": json.loads(r[3]), "source_claim_ids": json.loads(r[4]),
            "confidence": r[5], "review_state": r[6],
        } for r in rows]

    def latest_counterpoint(self, review_state: str | None = None) -> dict | None:
        rows = self.counterpoints()
        if review_state is not None:
            rows = [r for r in rows if r["review_state"] == review_state]
        return rows[-1] if rows else None

    def set_counterpoint_review(self, version: int, review_state: str) -> None:
        self._set_derived_review("counterpoint_versions", version, review_state)

    def _next_version(self, table: str) -> int:
        return int(self._conn.execute(
            f"SELECT COALESCE(MAX(version), 0) + 1 FROM {table}").fetchone()[0])

    def _set_derived_review(self, table: str, version: int, review_state: str) -> None:
        if review_state not in ("candidate", "approved", "rejected"):
            raise ValueError("review_state invalido")
        self._conn.execute(
            f"UPDATE {table} SET review_state=? WHERE version=?",
            (review_state, int(version)))
        self._conn.commit()

    # --- K3: decisioni di salienza aggregate-safe ----------------------
    def add_salience_decision(self, *, item_ref: str, action: str, score: float,
                              reasons: list[str], factors: dict) -> int:
        cur = self._conn.execute(
            "INSERT INTO salience_decisions "
            "(ts, item_ref, action, score, reasons, factors) VALUES (?,?,?,?,?,?)",
            (time.time(), item_ref, action, float(score),
             json.dumps(reasons, ensure_ascii=False), json.dumps(factors)))
        self._conn.commit()
        return cur.lastrowid

    def salience_decisions(self, limit: int | None = None) -> list[dict]:
        q = ("SELECT id, ts, item_ref, action, score, reasons, factors "
             "FROM salience_decisions ORDER BY id DESC")
        params: tuple = ()
        if limit is not None:
            q += " LIMIT ?"
            params = (int(limit),)
        return [{
            "id": r[0], "ts": r[1], "item_ref": r[2], "action": r[3],
            "score": r[4], "reasons": json.loads(r[5]), "factors": json.loads(r[6]),
        } for r in self._conn.execute(q, params)]

    # --- D1: proactivity queue + daemon state ---------------------------
    def enqueue_proactivity(self, *, candidate_id: str, category: str,
                            topic_ref: str, net_value: float,
                            expected_value: float, interruption_cost: float,
                            privacy_cost: float, trust_cost: float,
                            created_at: float, expiry: float | None) -> int:
        """Accoda una candidate di proattivita'. La coda NON contiene testo
        personale: solo categoria + riferimento opaco + numeri."""
        cur = self._conn.execute(
            "INSERT INTO proactivity_queue "
            "(candidate_id, created_at, category, topic_ref, net_value, "
            " expected_value, interruption_cost, privacy_cost, trust_cost, "
            " expiry, status, reasons) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,'queued','[]')",
            (candidate_id, float(created_at), category, topic_ref,
             float(net_value), float(expected_value), float(interruption_cost),
             float(privacy_cost), float(trust_cost),
             None if expiry is None else float(expiry)))
        self._conn.commit()
        return cur.lastrowid

    def proactivity_queue_items(self, status: str | None = None,
                                limit: int | None = None) -> list[dict]:
        q = ("SELECT id, candidate_id, created_at, category, topic_ref, "
             "net_value, expected_value, interruption_cost, privacy_cost, "
             "trust_cost, expiry, status, decided_at, reasons "
             "FROM proactivity_queue")
        params: list = []
        if status is not None:
            q += " WHERE status = ?"
            params.append(status)
        q += " ORDER BY id"
        if limit is not None:
            q += " LIMIT ?"
            params.append(int(limit))
        return [{
            "id": r[0], "candidate_id": r[1], "created_at": r[2],
            "category": r[3], "topic_ref": r[4], "net_value": r[5],
            "expected_value": r[6], "interruption_cost": r[7],
            "privacy_cost": r[8], "trust_cost": r[9], "expiry": r[10],
            "status": r[11], "decided_at": r[12], "reasons": json.loads(r[13]),
        } for r in self._conn.execute(q, tuple(params))]

    def set_proactivity_status(self, item_id: int, status: str, *,
                               net_value: float | None = None,
                               reasons: list[str] | None = None,
                               decided_at: float | None = None) -> None:
        self._conn.execute(
            "UPDATE proactivity_queue SET status = ?, "
            "net_value = COALESCE(?, net_value), "
            "reasons = COALESCE(?, reasons), "
            "decided_at = COALESCE(?, decided_at) WHERE id = ?",
            (status,
             None if net_value is None else float(net_value),
             None if reasons is None else json.dumps(reasons, ensure_ascii=False),
             None if decided_at is None else float(decided_at),
             int(item_id)))
        self._conn.commit()

    def proactivity_status_counts(self) -> dict:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) FROM proactivity_queue GROUP BY status")
        return {r[0]: r[1] for r in rows}

    def daemon_state(self) -> dict:
        row = self._conn.execute(
            "SELECT tick_count, last_heartbeat_at, last_emit_at "
            "FROM daemon_state WHERE id = 1").fetchone()
        if row is None:
            return {"tick_count": 0, "last_heartbeat_at": None, "last_emit_at": None}
        return {"tick_count": row[0], "last_heartbeat_at": row[1],
                "last_emit_at": row[2]}

    def update_daemon_state(self, *, tick_count: int,
                            last_heartbeat_at: float | None,
                            last_emit_at: float | None) -> None:
        self._conn.execute(
            "INSERT INTO daemon_state "
            "(id, tick_count, last_heartbeat_at, last_emit_at, updated_at) "
            "VALUES (1, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET tick_count = excluded.tick_count, "
            "last_heartbeat_at = excluded.last_heartbeat_at, "
            "last_emit_at = excluded.last_emit_at, updated_at = excluded.updated_at",
            (int(tick_count),
             None if last_heartbeat_at is None else float(last_heartbeat_at),
             None if last_emit_at is None else float(last_emit_at),
             time.time()))
        self._conn.commit()

    # --- D-OBS: observation consent + purge -----------------------------
    def set_observation_consent(self, obs_class: str, enabled: bool) -> None:
        self._conn.execute(
            "INSERT INTO observation_consent (obs_class, enabled, updated_at) "
            "VALUES (?,?,?) ON CONFLICT(obs_class) DO UPDATE SET "
            "enabled = excluded.enabled, updated_at = excluded.updated_at",
            (obs_class, 1 if enabled else 0, time.time()))
        self._conn.commit()

    def observation_consent_classes(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT obs_class FROM observation_consent WHERE enabled = 1")
        return [r[0] for r in rows]

    def purge_observation_candidates(self, subject: str | None = None) -> int:
        """Cancella le candidate-ipotesi derivate dall'osservazione (revoca).
        Solo claim candidate con subject `observed:%` (mai fatti promossi)."""
        if subject is None:
            cur = self._conn.execute(
                "DELETE FROM knowledge WHERE lifecycle_state = 'candidate' "
                "AND subject LIKE 'observed:%'")
        else:
            cur = self._conn.execute(
                "DELETE FROM knowledge WHERE lifecycle_state = 'candidate' "
                "AND subject = ?", (subject,))
        self._conn.commit()
        return cur.rowcount

    # --- preferences ----------------------------------------------------
    def set_preference(self, key: str, value: str, explicit: bool = True) -> None:
        self._conn.execute(
            "INSERT INTO preferences (created_at, key, value, explicit) VALUES (?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET created_at=excluded.created_at, "
            "value=excluded.value, explicit=excluded.explicit",
            (time.time(), key, value, int(explicit)))
        self._conn.commit()

    def preferences(self) -> dict:
        return {r[0]: r[1] for r in self._conn.execute("SELECT key, value FROM preferences")}

    def preference_records(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT key, value, explicit, created_at FROM preferences ORDER BY created_at"
        )
        return [
            {
                "key": row[0],
                "value": row[1],
                "explicit": bool(row[2]),
                "created_at": row[3],
            }
            for row in rows
        ]

    def delete_preferences_prefix(self, prefix: str) -> None:
        self._conn.execute("DELETE FROM preferences WHERE key LIKE ?", (f"{prefix}%",))
        self._conn.commit()

    # --- onboarding -------------------------------------------------------
    def onboarding_state(self) -> dict | None:
        row = self._conn.execute(
            "SELECT payload FROM onboarding_state WHERE id = 1"
        ).fetchone()
        return json.loads(row[0]) if row else None

    # --- voice consent (S11, separato dal consenso memoria) -------------
    def voice_consent(self) -> bool:
        row = self._conn.execute(
            "SELECT consent FROM voice_state WHERE id = 1").fetchone()
        return bool(row[0]) if row else False

    def set_voice_consent(self, granted: bool) -> None:
        self._conn.execute(
            "INSERT INTO voice_state (id, consent, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET consent=excluded.consent, "
            "updated_at=excluded.updated_at",
            (int(bool(granted)), time.time()))
        self._conn.commit()
        self.add_event("voice_consent", {"granted": bool(granted)})

    def set_onboarding_state(self, state: dict) -> None:
        self._conn.execute(
            "INSERT INTO onboarding_state (id, payload) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (json.dumps(state, ensure_ascii=False),),
        )
        self._conn.commit()

    def add_onboarding_item(
        self,
        kind: str,
        statement: str,
        confidence: float,
        explicit: bool,
        provenance: list[int],
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO onboarding_items "
            "(created_at, kind, statement, confidence, explicit, provenance) "
            "VALUES (?,?,?,?,?,?)",
            (
                time.time(),
                kind,
                statement,
                float(confidence),
                int(explicit),
                json.dumps(provenance),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def onboarding_items(self, kind: str | None = None) -> list[dict]:
        query = (
            "SELECT id, created_at, kind, statement, confidence, explicit, provenance "
            "FROM onboarding_items"
        )
        params: tuple = ()
        if kind is not None:
            query += " WHERE kind = ?"
            params = (kind,)
        query += " ORDER BY id"
        rows = self._conn.execute(query, params)
        return [
            {
                "id": row[0],
                "created_at": row[1],
                "kind": row[2],
                "statement": row[3],
                "confidence": row[4],
                "explicit": bool(row[5]),
                "provenance": json.loads(row[6]),
            }
            for row in rows
        ]

    def clear_onboarding(self) -> None:
        # Reset multi-tabella atomico: transazione esplicita (la connessione e'
        # in autocommit, vedi __init__).
        self._conn.execute("BEGIN")
        try:
            self._conn.execute("DELETE FROM onboarding_state")
            self._conn.execute("DELETE FROM onboarding_items")
            self._conn.execute("DELETE FROM preferences WHERE key LIKE 'onboarding:%'")
            self._conn.execute("DELETE FROM episodes WHERE category = 'onboarding'")
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    # --- personality runtime ----------------------------------------------
    def add_personality_decision(
        self,
        *,
        mode: str,
        explicit_mode: bool,
        counterpoint_required: bool,
        reasons: list[str],
        preference_keys: list[str],
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO personality_decisions "
            "(ts, mode, explicit_mode, counterpoint_required, reasons, preference_keys) "
            "VALUES (?,?,?,?,?,?)",
            (
                time.time(),
                mode,
                int(explicit_mode),
                int(counterpoint_required),
                json.dumps(reasons, ensure_ascii=False),
                json.dumps(preference_keys, ensure_ascii=False),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def finish_personality_decision(
        self, decision_id: int, violations: list[str], repaired: bool
    ) -> None:
        self._conn.execute(
            "UPDATE personality_decisions SET violations = ?, repaired = ? WHERE id = ?",
            (json.dumps(violations, ensure_ascii=False), int(repaired), decision_id),
        )
        self._conn.commit()

    def personality_decisions(self, limit: int | None = None) -> list[dict]:
        query = (
            "SELECT id, ts, mode, explicit_mode, counterpoint_required, reasons, "
            "preference_keys, violations, repaired FROM personality_decisions "
            "ORDER BY id DESC"
        )
        params: tuple = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        rows = self._conn.execute(query, params)
        return [
            {
                "id": row[0],
                "ts": row[1],
                "mode": row[2],
                "explicit_mode": bool(row[3]),
                "counterpoint_required": bool(row[4]),
                "reasons": json.loads(row[5]),
                "preference_keys": json.loads(row[6]),
                "violations": json.loads(row[7]),
                "repaired": bool(row[8]),
            }
            for row in rows
        ]

    # --- pii map (cifrata) ----------------------------------------------
    def pii_map_store(self, placeholder: str, value: str, label: str) -> None:
        enc = base64.b64encode(_dpapi_encrypt(value.encode("utf-8"))).decode("ascii")
        self._conn.execute(
            "INSERT OR IGNORE INTO pii_map (placeholder, value_enc, label, created_at) VALUES (?,?,?,?)",
            (placeholder, enc, label, time.time()))
        self._conn.commit()

    def pii_map_lookup(self, value: str) -> str | None:
        for placeholder, real in self.pii_map_all():
            if real == value:
                return placeholder
        return None

    def pii_map_count(self, label: str) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM pii_map WHERE label = ?", (label,)).fetchone()[0]

    def pii_map_all(self) -> list[tuple[str, str]]:
        out = []
        for placeholder, enc in self._conn.execute("SELECT placeholder, value_enc FROM pii_map"):
            try:
                out.append((placeholder, _dpapi_decrypt(base64.b64decode(enc)).decode("utf-8")))
            except Exception:
                continue
        return out

    # --- grants -----------------------------------------------------------
    def record_grant(self, capability_id: str, scope: str, decision: str, remembered: bool) -> None:
        self._conn.execute(
            "INSERT INTO grants (capability_id, scope, decision, remembered, created_at) VALUES (?,?,?,?,?)",
            (capability_id, scope, decision, int(remembered), time.time()))
        self._conn.commit()

    def find_grant(self, capability_id: str, scope: str) -> str | None:
        row = self._conn.execute(
            "SELECT decision FROM grants WHERE capability_id=? AND scope=? AND remembered=1 "
            "ORDER BY created_at DESC LIMIT 1", (capability_id, scope)).fetchone()
        return row[0] if row else None

    # --- capability stats --------------------------------------------------
    def bump_capability(self, capability_id: str, success: bool) -> None:
        self._conn.execute(
            "INSERT INTO capability_stats (capability_id, invocations, successes, failures, last_used) "
            "VALUES (?,1,?,?,?) ON CONFLICT(capability_id) DO UPDATE SET "
            "invocations=invocations+1, successes=successes+excluded.successes, "
            "failures=failures+excluded.failures, last_used=excluded.last_used",
            (capability_id, int(success), int(not success), time.time()))
        self._conn.commit()

    def capability_stats(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT capability_id, invocations, successes, failures, last_used FROM capability_stats")
        return [{"capability_id": r[0], "invocations": r[1], "successes": r[2],
                 "failures": r[3], "last_used": r[4]} for r in rows]

    # --- aliases (command router) ---------------------------------------------
    def alias_store(self, normalized: str, intent: str, args: dict | None = None) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO aliases (normalized, intent, args, created_at, hits) "
            "VALUES (?,?,?,?, COALESCE((SELECT hits FROM aliases WHERE normalized=?),0))",
            (normalized, intent, json.dumps(args or {}, ensure_ascii=False),
             time.time(), normalized))
        self._conn.commit()

    def alias_lookup(self, normalized: str) -> dict | None:
        row = self._conn.execute(
            "SELECT intent, args FROM aliases WHERE normalized = ?", (normalized,)).fetchone()
        if not row:
            return None
        self._conn.execute("UPDATE aliases SET hits = hits + 1 WHERE normalized = ?",
                           (normalized,))
        self._conn.commit()
        return {"intent": row[0], "args": json.loads(row[1])}

    def alias_all(self) -> dict[str, dict]:
        return {r[0]: {"intent": r[1], "args": json.loads(r[2])}
                for r in self._conn.execute("SELECT normalized, intent, args FROM aliases")}

    def prune_aliases_for_intents(self, intents) -> int:
        """Elimina gli alias appresi che puntano a uno degli intent dati.
        Usato per ripulire recall indovinati male dal normalizzatore."""
        intents = tuple(intents)
        if not intents:
            return 0
        placeholders = ",".join("?" for _ in intents)
        cur = self._conn.execute(
            f"DELETE FROM aliases WHERE intent IN ({placeholders})", intents)
        self._conn.commit()
        return cur.rowcount

    # --- events (telemetria) -------------------------------------------------
    def add_event(self, kind: str, payload: dict) -> None:
        self._conn.execute("INSERT INTO events (ts, kind, payload) VALUES (?,?,?)",
                           (time.time(), kind, json.dumps(payload, ensure_ascii=False)))
        self._conn.commit()

    def events_since(self, ts: float) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts, kind, payload FROM events WHERE ts >= ? ORDER BY ts", (ts,))
        return [{"ts": r[0], "kind": r[1], "payload": json.loads(r[2])} for r in rows]

    def close(self) -> None:
        self._conn.close()
