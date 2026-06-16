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
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

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
        self._conn.execute("DELETE FROM onboarding_state")
        self._conn.execute("DELETE FROM onboarding_items")
        self._conn.execute("DELETE FROM preferences WHERE key LIKE 'onboarding:%'")
        self._conn.execute("DELETE FROM episodes WHERE category = 'onboarding'")
        self._conn.commit()

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
