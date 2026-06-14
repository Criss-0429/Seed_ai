"""Automation around exposure evidence; final promotion remains owner-gated."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .evaluator import EvaluatorHarness
from .promotion import PromotionError


class MutationLifecycle:
    def __init__(self, lineage, promotion, proposals_root: Path, *, enabled: bool = True,
                 canary_context: str = "desktop-session", audit=None):
        self.lineage, self.promotion = lineage, promotion
        self.proposals_root = Path(proposals_root)
        self.enabled, self.canary_context = bool(enabled), canary_context
        self.audit = audit or (lambda kind, payload: None)
        self.proposals_root.mkdir(parents=True, exist_ok=True)

    def advance(self, *, owner_approved_canary: bool = False,
                canary_probe=None) -> list[dict]:
        """Advance safely using real recorded evidence; never calls promote()."""
        if not self.enabled:
            return []
        actions: list[dict] = []
        for candidate in self._candidates():
            try:
                if candidate.status == "shadow":
                    self._record_evaluator_shadow(candidate)
                    candidate = self.lineage.candidate(candidate.mutation_id)
                    if not self.promotion._exposure_blockers(
                            candidate, "shadow", self.promotion.policy.min_shadow_passes):
                        lease = self.promotion.start_canary(
                            candidate, [self.canary_context],
                            owner_approved=owner_approved_canary)
                        actions.append({"mutation_id": candidate.mutation_id,
                                        "action": "canary_started",
                                        "expires_at": lease.expires_at})
                elif candidate.status == "canary" and canary_probe is not None:
                    outcome, metrics, blocking = canary_probe(candidate, self.canary_context)
                    self.promotion.observe(candidate.mutation_id, "canary", outcome,
                                           "automation:runtime-probe", metrics,
                                           blocking, self.canary_context)
                    candidate = self.lineage.candidate(candidate.mutation_id)
                if candidate.status == "canary":
                    blockers = self.promotion.promotion_blockers(candidate)
                    if not blockers:
                        actions.append(self._write_promotion_proposal(candidate))
            except PromotionError as exc:
                actions.append({"mutation_id": candidate.mutation_id,
                                "action": "blocked", "reason": str(exc)})
        if actions:
            self.audit("mutation_lifecycle_advanced", {"actions": len(actions)})
        return actions

    def _record_evaluator_shadow(self, candidate) -> None:
        existing = self.lineage.exposure_observations(candidate.mutation_id, "shadow")
        source = "automation:independent-evaluator"
        if any(item.get("source") == source for item in existing):
            return
        outcome = self.lineage.latest_evaluation_outcome(
            candidate.mutation_id, EvaluatorHarness.EVALUATOR_ID)
        if outcome == "pass":
            for _ in range(self.promotion.policy.min_shadow_passes):
                self.promotion.observe(candidate.mutation_id, "shadow", "pass", source,
                                       {"real_effects": False})

    def _write_promotion_proposal(self, candidate) -> dict:
        path = self.proposals_root / f"{candidate.mutation_id}.json"
        payload = {
            "schema_version": "seed.promotion-proposal.v1",
            "mutation_id": candidate.mutation_id,
            "created_at": time.time(),
            "owner_approval_required": True,
            "blockers": [],
        }
        if not path.exists():
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"mutation_id": candidate.mutation_id, "action": "promotion_proposed",
                "proposal": str(path)}

    def _candidates(self):
        ids = {
            event["mutation_id"] for event in self.lineage.events()
            if event["event_type"] == "candidate_created"
        }
        return [candidate for mid in sorted(ids)
                if (candidate := self.lineage.candidate(mid)) is not None]


