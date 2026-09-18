"""Tests: Brier/ECE math, calibration log, HLoop prediction+outcome wiring."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dash.hloop import HLoop  # noqa: E402
from qp.calibration import CalibrationLog, brier, ece  # noqa: E402
import sqlite3  # noqa: E402


def test_brier_ece():
    assert brier([]) is None and ece([]) is None
    assert brier([(1.0, 1), (0.0, 0)]) == 0.0
    assert brier([(1.0, 0)]) == 1.0
    assert ece([(0.9, 1), (0.9, 1), (0.1, 0)]) is not None
    perfect = ece([(0.9, 1)] * 9 + [(0.1, 0)] * 1)
    bad = ece([(0.9, 0)] * 9 + [(0.1, 0)] * 1)
    assert perfect < bad


def test_log_report(tmp_path=None):
    import tempfile
    db = sqlite3.connect(tempfile.mktemp(suffix=".db"))
    log = CalibrationLog(db)
    log.log_prediction("r1", "triage", 0.8)
    log.log_prediction("r2", "triage", 0.2)
    log.log_outcome("r1", 1)
    rep = log.report()
    assert rep["scored"] == 1 and rep["pending"] == 1
    assert rep["families"]["triage"]["n"] == 1
    try:
        log.log_prediction("r3", "triage", 2.0)
        raise SystemExit("bad p accepted")
    except ValueError:
        pass


def test_hloop_wiring(tmp_path):
    h = HLoop(str(tmp_path / "h.db"))
    ref = h.present({"id": "T-1"}, family="triage", pred_p=0.7)
    h.decide("T-1", ref, outcome=1)
    rep = h.calibration()
    assert rep["families"]["triage"]["n"] == 1 and rep["scored"] == 1
    # backward compatible: no p, no outcome
    ref2 = h.present({"id": "T-2"})
    h.decide("T-2", ref2)
    assert h.calibration()["scored"] == 1
