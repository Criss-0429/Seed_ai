"""Test K4 predict-calibrate + M4 safety gate/stale cascade."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import calibration  # noqa: E402
from seed.core.knowledge import KnowledgeStore, UserClaim  # noqa: E402
from seed.core.memory import Memory  # noqa: E402


def _store(tmp_path):
    mem = Memory(tmp_path / "c.db")
    return KnowledgeStore(mem), mem


# -- predizioni -------------------------------------------------------------

def test_register_opens_prediction_for_pattern(tmp_path):
    store, mem = _store(tmp_path)
    store.record(UserClaim("pattern", "domeniche", "difficili",
                           confidence_source="inferred"))
    opened = calibration.register_predictions(mem)
    assert opened == 1
    assert len(mem.open_predictions()) == 1


def test_register_no_duplicate_open_prediction(tmp_path):
    store, mem = _store(tmp_path)
    store.record(UserClaim("pattern", "x", "y", confidence_source="inferred"))
    calibration.register_predictions(mem)
    assert calibration.register_predictions(mem) == 0      # gia' aperta


def test_non_pattern_does_not_predict(tmp_path):
    store, mem = _store(tmp_path)
    store.record(UserClaim("relation", "residenza", "Milano"))
    assert calibration.register_predictions(mem) == 0


# -- risoluzione + calibrazione ---------------------------------------------

def test_refuted_prediction_lowers_pattern_confidence(tmp_path):
    store, mem = _store(tmp_path)
    store.record(UserClaim("pattern", "x", "y", confidence=0.45,
                           confidence_source="inferred"))
    calibration.register_predictions(mem)
    pred = mem.open_predictions()[0]
    before = next(k for k in mem.all_knowledge() if k["id"] == pred["source_claim_id"])
    calibration.resolve_prediction(mem, pred["id"], observed=False)
    after = next(k for k in mem.all_knowledge() if k["id"] == pred["source_claim_id"])
    assert after["confidence"] < before["confidence"]
    assert mem.open_predictions() == []


def test_calibration_report_brier(tmp_path):
    store, mem = _store(tmp_path)
    store.record(UserClaim("pattern", "x", "y", confidence=1.0,
                           confidence_source="inferred"))
    calibration.register_predictions(mem)
    pred = mem.open_predictions()[0]
    calibration.resolve_prediction(mem, pred["id"], observed=True)
    rep = calibration.calibration_report(mem)
    assert rep.resolved == 1 and rep.confirmed == 1
    assert rep.brier is not None and 0.0 <= rep.brier <= 1.0


def test_calibration_report_empty(tmp_path):
    _, mem = _store(tmp_path)
    assert calibration.calibration_report(mem).brier is None


# -- safety gate: sensibile -> candidate ------------------------------------

def test_sensitive_explicit_claim_stays_candidate(tmp_path):
    store, mem = _store(tmp_path)
    out = store.record(UserClaim("fact", "salute", "diagnosi X",
                                 confidence_source="explicit",
                                 sensitivity="sensitive"))
    assert out["lifecycle"] == "candidate"          # non attivo finche' non confermato
    assert mem.active_knowledge() == []


# -- stale cascade su supersession ------------------------------------------

def test_supersession_closes_old_edges_keeps_history(tmp_path):
    store, mem = _store(tmp_path)
    out = store.record(UserClaim("relation", "residenza", "Milano"))
    old_id = out["id"]
    mem.add_edge(source_id=old_id, target_id=999, edge_type="supports")
    store.record(UserClaim("relation", "residenza", "Roma"))   # supersede
    active_edges = mem.all_edges()
    types = [e["edge_type"] for e in active_edges]
    assert "supports" not in types          # edge vecchio chiuso (stale cascade)
    assert "supersedes" in types            # storia mantenuta
    mem.close()
