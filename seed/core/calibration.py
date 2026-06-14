"""K4 predict-calibrate.

Wiki harness: "ogni pattern maturo deve predire qualcosa. Se non predice, e'
narrativa." Qui ogni pattern produce una predizione tipizzata (orizzonte +
finestra di osservazione); la predizione viene risolta contro l'osservazione e
calibrata (Brier). Pattern smentito -> confidenza giu' (il counterpoint, K2, lo
rigenera dai claim deboli). Deterministico, zero token.
"""

from __future__ import annotations

from dataclasses import dataclass

_HORIZON_DAYS = 7
_WINDOW_DAYS = 7
_REFUTE_DECAY = 0.6           # confidenza del pattern smentito


@dataclass(frozen=True)
class CalibrationReport:
    resolved: int
    confirmed: int
    refuted: int
    brier: float | None       # 0 = perfetto, None se nulla di risolto


def register_predictions(memory) -> int:
    """Apre una predizione per ogni pattern senza una gia' aperta. Ritorna
    quante ne ha aperte."""
    opened = 0
    for c in memory.all_knowledge():
        if c["claim_type"] != "pattern":
            continue
        if c["lifecycle_state"] not in ("candidate", "active"):
            continue
        if c["superseded_at"] is not None:
            continue
        if memory.has_open_prediction(c["id"]):
            continue
        memory.add_prediction(
            source_claim_id=c["id"],
            predicted_event=f"{c['subject']}: {c['value']}",
            probability=max(0.0, min(1.0, float(c["confidence"]))),
            horizon_days=_HORIZON_DAYS,
            observation_window_days=_WINDOW_DAYS)
        opened += 1
    if opened:
        memory.add_event("predictions_opened", {"count": opened})
    return opened


def resolve_prediction(memory, prediction_id: int, *, observed: bool) -> dict:
    """Risolve una predizione. Smentita -> abbassa la confidenza del pattern
    fonte (la correzione/osservazione prevale sull'inferenza)."""
    outcome = "confirmed" if observed else "refuted"
    pred = next((p for p in memory.all_predictions() if p["id"] == prediction_id), None)
    memory.resolve_prediction(prediction_id, outcome)
    if pred is not None and not observed:
        src = pred["source_claim_id"]
        row = next((k for k in memory.all_knowledge() if k["id"] == src), None)
        if row is not None:
            memory.set_knowledge_confidence(src, float(row["confidence"]) * _REFUTE_DECAY)
    memory.add_event("prediction_resolved", {"outcome": outcome})
    return {"outcome": outcome}


def calibration_report(memory) -> CalibrationReport:
    """Brier score sulle predizioni risolte: media di (probabilita - esito)^2."""
    resolved = [p for p in memory.all_predictions()
                if p["outcome"] in ("confirmed", "refuted")]
    if not resolved:
        return CalibrationReport(0, 0, 0, None)
    confirmed = sum(1 for p in resolved if p["outcome"] == "confirmed")
    refuted = sum(1 for p in resolved if p["outcome"] == "refuted")
    brier = sum(
        (float(p["probability"]) - (1.0 if p["outcome"] == "confirmed" else 0.0)) ** 2
        for p in resolved) / len(resolved)
    return CalibrationReport(len(resolved), confirmed, refuted, round(brier, 4))
