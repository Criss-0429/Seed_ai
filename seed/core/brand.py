"""Deterministic evolving brand driven by confirmed local events."""

from __future__ import annotations

import hashlib


class BrandEvolution:
    def __init__(self, memory, manifest_provider, manifest_writer, audit=None):
        self.memory = memory
        self.manifest_provider = manifest_provider
        self.manifest_writer = manifest_writer
        self.audit = audit or (lambda kind, payload: None)

    def refresh(self, seed: str = "seed") -> dict:
        manifest = self.manifest_provider()
        theme = manifest.setdefault("theme", {})
        events = self.memory.events_since(0)
        confirmed = sum(e["kind"] in {
            "onboarding_completed", "survey", "rollback", "capability_forged",
            "promotion", "knowledge_reviewed"} for e in events)
        hue = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 360
        maturity = min(1.0, confirmed / 24.0)
        changed = (
            theme.get("hue") != hue
            or theme.get("chroma") != round(0.015 + maturity * 0.085, 3)
            or theme.get("maturity") != round(maturity, 3)
        )
        theme.update({
            "hue": hue,
            "chroma": round(0.015 + maturity * 0.085, 3),
            "maturity": round(maturity, 3),
            "maturity_events": confirmed,
        })
        if changed:
            manifest["version"] = int(manifest.get("version", 0)) + 1
            self.manifest_writer(manifest)
            self.audit("brand_refreshed", {"maturity": round(maturity, 1),
                                            "events": confirmed})
        return manifest


