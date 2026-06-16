"""Telemetria locale e report d'esperimento.

Tutto resta sul PC. Il report finale e' un JSON di AGGREGATI leggibile,
esportato MANUALMENTE dall'utente a fine settimana (doc 03/06):
niente testi grezzi, niente titoli finestra, niente pii_map.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path

from . import forbidden

log = logging.getLogger("seed.telemetry")


class Telemetry:
    def __init__(self, memory, evolution):
        self._memory = memory
        self._evolution = evolution

    def record_survey(self, usefulness: int, surprise: str) -> None:
        """Micro-survey serale: 2 domande, 10 secondi."""
        self._memory.add_event("survey", {
            "usefulness_1_5": max(1, min(5, int(usefulness))),
            "surprised": bool(surprise.strip()),
            # la risposta libera passa nel diario di reflection ma NON nel report
        })
        self._memory.add_episode("survey", {"usefulness": usefulness,
                                            "surprise": surprise}, category="survey")

    # ------------------------------------------------------------------
    def build_report(self) -> dict:
        """Aggregati per la tesi. Leggibile di proposito: l'utente lo apre
        e lo legge prima di decidere di mandarlo."""
        events = self._memory.events_since(0)
        stats = self._memory.capability_stats()
        versions = sorted(p.name for p in self._evolution.versions_dir.iterdir()
                          if p.is_dir()) if self._evolution.versions_dir.exists() else []

        usage_by_category: dict[str, float] = {}
        for ep in self._memory.episodes_since(0):
            if ep["source"] == "watcher":
                cat = ep["payload"].get("category", "altro")
                usage_by_category[cat] = usage_by_category.get(cat, 0) + \
                    ep["payload"].get("duration_s", 0)

        def _count(kind: str, **match) -> int:
            n = 0
            for e in events:
                if e["kind"] != kind:
                    continue
                if all(e["payload"].get(k) == v for k, v in match.items()):
                    n += 1
            return n

        surveys = [e["payload"] for e in events if e["kind"] == "survey"]
        lineage = self._lineage_summary()
        personality = self._personality_summary()
        research = self._research_summary(events)
        models = self._models_summary(events)
        knowledge = self._knowledge_summary()
        salience = self._salience_summary()

        return {
            "report_version": 1,
            "generated": date.today().isoformat(),
            "nota": "Questo report contiene SOLO aggregati. Nessun testo delle tue "
                    "conversazioni, nessun titolo di finestra, nessun dato personale. "
                    "Leggilo: se qualcosa non ti torna, non inviarlo.",
            "capability_fingerprint": {
                "active": [s["capability_id"] for s in stats if s["invocations"] > 0],
                "stats": stats,
            },
            "legacy_evolution_user_model": self._evolution.user_model(),
            "personality": personality,
            "research": research,
            "models": models,
            "knowledge": knowledge,
            "salience": salience,
            "evolution": {
                "snapshots": versions,
                "reflections_run": _count("reflection"),
                "rollbacks": _count("rollback"),
                "capabilities_forged": _count("capability_forged"),
                "capabilities_pruned": _count("capability_pruned"),
                "lineage": lineage,
            },
            "permissions": {
                "granted": _count("permission", decision="allow"),
                "denied": _count("permission", decision="deny"),
            },
            "watcher": {
                "hours_by_category": {k: round(v / 3600, 2)
                                      for k, v in usage_by_category.items()},
                "pauses": _count("watcher_paused"),
            },
            "surveys": {
                "daily_usefulness": [s.get("usefulness_1_5") for s in surveys],
                "days_with_surprise": sum(1 for s in surveys if s.get("surprised")),
            },
        }

    def _research_summary(self, events: list[dict]) -> dict:
        """Aggregati S9: mai query, mai key, mai testo dei risultati."""
        calls = [e["payload"] for e in events if e["kind"] == "research_call"]
        blocked = [e["payload"] for e in events if e["kind"] == "research_blocked"]
        by_provider: dict[str, int] = {}
        by_depth: dict[str, int] = {}
        for c in calls:
            prov = c.get("provider") or "none"
            by_provider[prov] = by_provider.get(prov, 0) + 1
            depth = c.get("depth")
            if depth:
                by_depth[depth] = by_depth.get(depth, 0) + 1
        blocked_reasons: dict[str, int] = {}
        for b in blocked:
            reason = b.get("reason", "unknown")
            blocked_reasons[reason] = blocked_reasons.get(reason, 0) + 1
        return {
            "calls": len(calls),
            "ok": sum(1 for c in calls if c.get("ok")),
            "fallbacks": sum(1 for c in calls if c.get("fallback_used")),
            "by_provider": by_provider,
            "by_depth": by_depth,
            "results_total": sum(int(c.get("results", 0)) for c in calls),
            "flagged_results": sum(int(c.get("flagged_results", 0)) for c in calls),
            "synthesis_rejected": sum(
                1 for e in events if e["kind"] == "research_synthesis_rejected"),
            "blocked": blocked_reasons,
        }

    def _models_summary(self, events: list[dict]) -> dict:
        """Aggregati S10: separazione ruoli, fallback e costo (token).
        Mai prompt, contenuto o key — solo ruolo, modello id (pubblico) e conteggi."""
        calls = [e["payload"] for e in events if e["kind"] == "model_call"]
        by_role: dict[str, int] = {}
        by_model: dict[str, int] = {}
        ok = fallbacks = tokens = 0
        for c in calls:
            role = c.get("role") or "?"
            model = c.get("model") or "?"
            by_role[role] = by_role.get(role, 0) + 1
            by_model[model] = by_model.get(model, 0) + 1
            ok += 1 if c.get("ok") else 0
            fallbacks += 1 if c.get("fallback") else 0
            tokens += int(c.get("tokens") or 0)
        reviews = [e["payload"] for e in events if e["kind"] == "design_review"]
        verdicts: dict[str, int] = {}
        for r in reviews:
            v = r.get("verdict", "unknown")
            verdicts[v] = verdicts.get(v, 0) + 1
        return {
            "calls": len(calls),
            "ok": ok,
            "fallbacks": fallbacks,
            "by_role": by_role,
            "by_model": by_model,
            "tokens_total": tokens,
            "reviews": {
                "total": len(reviews),
                "verdicts": verdicts,
                "blocking_total": sum(int(r.get("blocking", 0)) for r in reviews),
            },
        }

    def _knowledge_summary(self) -> dict:
        """Aggregati M2: tipi e stati dei claim. Mai i valori (sarebbe testo
        personale): solo conteggi. Lo staleness e' superseded/total."""
        rows = self._memory.all_knowledge()
        by_type: dict[str, int] = {}
        by_lifecycle: dict[str, int] = {}
        for r in rows:
            by_type[r["claim_type"]] = by_type.get(r["claim_type"], 0) + 1
            by_lifecycle[r["lifecycle_state"]] = \
                by_lifecycle.get(r["lifecycle_state"], 0) + 1
        return {
            "total": len(rows),
            "active": by_lifecycle.get("active", 0),
            "candidate": by_lifecycle.get("candidate", 0),
            "superseded": by_lifecycle.get("superseded", 0),
            "by_type": by_type,
            "living_profile_versions": self._derived_counts(
                self._memory.living_profiles()),
            "counterpoint_versions": self._derived_counts(
                self._memory.counterpoints()),
            "latest_living_profile": self._latest_derived_state(
                self._memory.latest_living_profile()),
            "latest_counterpoint": self._latest_derived_state(
                self._memory.latest_counterpoint()),
        }

    @staticmethod
    def _derived_counts(rows: list[dict]) -> dict:
        states: dict[str, int] = {}
        for row in rows:
            state = row["review_state"]
            states[state] = states.get(state, 0) + 1
        return {"total": len(rows), "by_review_state": states}

    @staticmethod
    def _latest_derived_state(row: dict | None) -> dict:
        if row is None:
            return {"version": None, "review_state": None}
        return {"version": row["version"], "review_state": row["review_state"]}

    def _personality_summary(self) -> dict:
        decisions = self._memory.personality_decisions()
        modes: dict[str, int] = {}
        for decision in decisions:
            mode = decision["mode"]
            modes[mode] = modes.get(mode, 0) + 1
        return {
            "decisions": len(decisions),
            "modes": modes,
            "counterpoint_turns": sum(
                1 for decision in decisions if decision["counterpoint_required"]
            ),
            "responses_with_violations": sum(
                1 for decision in decisions if decision["violations"]
            ),
            "repaired_responses": sum(
                1 for decision in decisions if decision["repaired"]
            ),
        }

    def _salience_summary(self) -> dict:
        rows = self._memory.salience_decisions()
        actions: dict[str, int] = {}
        for row in rows:
            actions[row["action"]] = actions.get(row["action"], 0) + 1
        return {"decisions": len(rows), "by_action": actions}

    def _lineage_summary(self) -> dict:
        """Aggregate-only lineage audit. Never exports proposals or evidence."""
        store = getattr(self._evolution, "lineage", None)
        if store is None:
            return {"available": False, "integrity_ok": None}
        try:
            integrity_ok = store.verify_integrity()
            events = store.events()
        except Exception:
            return {"available": True, "integrity_ok": False}
        candidate_ids = {
            event["mutation_id"] for event in events
            if event["event_type"] == "candidate_created"
        }
        statuses: dict[str, int] = {}
        for mutation_id in candidate_ids:
            status = store.current_status(mutation_id) or "unknown"
            statuses[status] = statuses.get(status, 0) + 1
        exposure_starts = {"shadow": 0, "canary": 0}
        promotion_decisions: dict[str, int] = {}
        for event in events:
            if event["event_type"] == "exposure_started":
                phase = event["payload"].get("phase", "unknown")
                exposure_starts[phase] = exposure_starts.get(phase, 0) + 1
            elif event["event_type"] == "promotion_decision":
                decision = event["payload"].get("decision", "unknown")
                promotion_decisions[decision] = promotion_decisions.get(decision, 0) + 1
        return {
            "available": True,
            "integrity_ok": integrity_ok,
            "candidates": len(candidate_ids),
            "evaluations": sum(
                1 for event in events if event["event_type"] == "evaluation_recorded"),
            "status_counts": statuses,
            "exposure_starts": exposure_starts,
            "exposure_observations": sum(
                1 for event in events if event["event_type"] == "exposure_observation"),
            "promotion_authorizations": sum(
                1 for event in events if event["event_type"] == "promotion_authorized"),
            "promotion_decisions": promotion_decisions,
            "lineage_rollbacks": sum(
                1 for event in events if event["event_type"] == "rollback_recorded"),
        }

    def export_report(self) -> Path:
        """Bottone 'Esporta report' nella UI: scrive nel workspace e ritorna il path."""
        out = forbidden.workspace_dir() / f"seed_report_{date.today().isoformat()}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.build_report(), ensure_ascii=False, indent=2),
                       encoding="utf-8")
        self._memory.add_event("report_exported", {"at": time.time()})
        return out
