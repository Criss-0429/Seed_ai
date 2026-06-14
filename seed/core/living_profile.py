"""K2: viste rigenerabili e reviewable del modello utente.

Il source of truth resta `knowledge`. Profilo e counterpoint sono derivati
versionati: il primo contiene solo claim attivi; il secondo mantiene dubbi e
letture deboli separati dai fatti.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LivingProfile:
    version: int
    generated_at: float
    sections: dict
    source_claim_ids: tuple[int, ...]


@dataclass(frozen=True)
class CounterpointFragment:
    topic: str
    reason: str
    confidence: float
    source_claim_ids: tuple[int, ...]


class LivingProfileBuilder:
    """Rigenera K2 in modo deterministico, senza patch incrementali."""

    def __init__(self, memory):
        self._memory = memory

    def rebuild(self) -> dict:
        profile_changed = self._rebuild_profile()
        counterpoint_changed = self._rebuild_counterpoint()
        self._memory.add_event("living_profile_rebuilt", {
            "profile_changed": profile_changed,
            "counterpoint_changed": counterpoint_changed,
        })
        return {
            "profile_changed": profile_changed,
            "counterpoint_changed": counterpoint_changed,
        }

    def approved_context(self, *, channel: str = "private_1to1",
                         source_claim_ids: set[int] | None = None) -> tuple[dict, list]:
        """Solo il privato 1:1 puo' leggere derivati approvati."""
        if channel != "private_1to1":
            return {}, []
        profile = self._memory.latest_living_profile("approved")
        counterpoint = self._memory.latest_counterpoint("approved")
        sections = profile["sections"] if profile else {}
        if source_claim_ids is not None:
            sections = {
                section: [
                    item for item in items
                    if item.get("source_claim_id") in source_claim_ids
                ]
                for section, items in sections.items()
            }
            sections = {key: items for key, items in sections.items() if items}
        return sections, counterpoint["fragments"] if counterpoint else []

    def _rebuild_profile(self) -> bool:
        claims = [
            c for c in self._memory.active_knowledge()
            if c["scope"] == "private" and c["sensitivity"] == "normal"
        ]
        claims.sort(key=lambda c: (c["claim_type"], c["subject"], c["id"]))
        sections: dict[str, list[dict]] = {}
        for claim in claims:
            sections.setdefault(claim["claim_type"], []).append({
                "subject": claim["subject"],
                "value": claim["value"],
                "confidence": claim["confidence"],
                "source_claim_id": claim["id"],
            })
        source_ids = [c["id"] for c in claims]
        previous = self._memory.latest_living_profile()
        if previous and previous["sections"] == sections:
            return False
        previous_ids = set(previous["source_claim_ids"]) if previous else set()
        current_ids = set(source_ids)
        delta = {
            "added_claim_ids": sorted(current_ids - previous_ids),
            "removed_claim_ids": sorted(previous_ids - current_ids),
        }
        confidence = (
            sum(c["confidence"] for c in claims) / len(claims) if claims else 0.0
        )
        self._memory.add_living_profile(
            sections=sections, source_claim_ids=source_ids, delta=delta,
            confidence=confidence)
        return True

    def _rebuild_counterpoint(self) -> bool:
        weak = [
            c for c in self._memory.all_knowledge()
            if c["lifecycle_state"] == "candidate"
            and c["claim_type"] in ("hypothesis", "pattern")
            and c["scope"] == "private"
            and c["sensitivity"] == "normal"
        ]
        weak.sort(key=lambda c: (c["claim_type"], c["subject"], c["id"]))
        fragments = [{
            "topic": c["subject"],
            "reason": f"Lettura non confermata: {c['value']}",
            "confidence": c["confidence"],
            "source_claim_ids": [c["id"]],
        } for c in weak]
        source_ids = [c["id"] for c in weak]
        previous = self._memory.latest_counterpoint()
        if previous and previous["fragments"] == fragments:
            return False
        confidence = (
            sum(c["confidence"] for c in weak) / len(weak) if weak else 0.0
        )
        self._memory.add_counterpoint(
            fragments=fragments, source_claim_ids=source_ids,
            confidence=confidence)
        return True
