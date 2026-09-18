"""Must-fail fixtures: every grant-abuse path rejected. If any of these
pass, the money core is broken. Plus the happy path and drift boundary."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nacl.signing import SigningKey  # noqa: E402

from qp.authority import issue, payload_hash  # noqa: E402
from qp.spend import SpendLedger  # noqa: E402

KEY = SigningKey.generate()
VERIFY = KEY.verify_key
ISSUER = "test-issuer"


def _grant(idem, amount, **kw):
    return issue("spend.authorize", {"idem": idem, "amount": amount},
                 "test-subject", ISSUER, KEY, **kw)


def _ledger(tmp_path, name="spend.db"):
    return SpendLedger(str(tmp_path / name))


def test_happy_path(tmp_path):
    L = _ledger(tmp_path)
    assert L.propose("s1", "test", 500, 1000) == "PROPOSED"
    assert L.propose("s1", "test", 500, 1000) == "PROPOSED"  # idempotent
    assert L.authorize("s1", _grant("s1", 500), {"idem": "s1", "amount": 500}, VERIFY) == "AUTHORIZED"
    assert L.settle("s1", 500) == "SETTLED"


def test_over_cap_refused(tmp_path):
    L = _ledger(tmp_path)
    try:
        L.propose("s2", "test", 1500, 1000)
        raise SystemExit("over-cap accepted")
    except ValueError:
        pass


def test_replay_rejected(tmp_path):
    L = _ledger(tmp_path)
    L.propose("s3", "test", 500, 1000)
    L.authorize("s3", _grant("s3", 500), {"idem": "s3", "amount": 500}, VERIFY)
    try:  # same grant object is single-use; state also moved on
        L.authorize("s3", _grant("s3", 500), {"idem": "s3", "amount": 500}, VERIFY)
        raise SystemExit("replay accepted")
    except ValueError:
        pass


def test_tampered_payload_rejected(tmp_path):
    L = _ledger(tmp_path)
    L.propose("s4", "test", 500, 1000)
    g = _grant("s4", 500)
    try:
        L.authorize("s4", g, {"idem": "s4", "amount": 900}, VERIFY)
        raise SystemExit("tampered payload accepted")
    except ValueError:
        pass


def test_wrong_key_rejected(tmp_path):
    L = _ledger(tmp_path)
    L.propose("s5", "test", 500, 1000)
    other = SigningKey.generate()
    g = issue("spend.authorize", {"idem": "s5", "amount": 500},
              "test-subject", ISSUER, other)
    try:
        L.authorize("s5", g, {"idem": "s5", "amount": 500}, VERIFY)
        raise SystemExit("forged signature accepted")
    except ValueError:
        pass


def test_expired_rejected(tmp_path):
    L = _ledger(tmp_path)
    L.propose("s6", "test", 500, 1000)
    g = _grant("s6", 500, ttl_s=-1)
    time.sleep(0.01)
    try:
        L.authorize("s6", g, {"idem": "s6", "amount": 500}, VERIFY)
        raise SystemExit("expired grant accepted")
    except ValueError:
        pass


def test_no_readback_no_settle(tmp_path):
    L = _ledger(tmp_path)
    L.propose("s7", "test", 500, 1000)
    L.authorize("s7", _grant("s7", 500), {"idem": "s7", "amount": 500}, VERIFY)
    try:
        L.settle("s7", -1)
        raise SystemExit("attempt settled without readback")
    except ValueError:
        pass


def test_drift_boundary(tmp_path):
    L = _ledger(tmp_path)
    L.propose("s8", "test", 1000, 2000)
    L.authorize("s8", _grant("s8", 1000), {"idem": "s8", "amount": 1000}, VERIFY)
    assert L.settle("s8", 1100) == "SETTLED"  # exactly 10% ok
    L2 = _ledger(tmp_path, "spend2.db")
    L2.propose("s9", "test", 1000, 2000)
    L2.authorize("s9", _grant("s9", 1000), {"idem": "s9", "amount": 1000}, VERIFY)
    assert L2.settle("s9", 1101) == "FLAGGED_DRIFT"


def test_settle_emits_verifiable_receipt(tmp_path, monkeypatch):
    import json
    log = str(tmp_path / "rc.jsonl")
    monkeypatch.setenv("RECEIPT_LOG", log)
    L = _ledger(tmp_path)
    L.propose("sr1", "test", 500, 1000)
    L.authorize("sr1", _grant("sr1", 500), {"idem": "sr1", "amount": 500}, VERIFY)
    assert L.settle("sr1", 500) == "SETTLED"
    entry = json.loads(open(log).read().strip().split("\n")[-1])
    rc, ev = entry["payload"]["receipt"], entry["payload"]["evidence"]
    assert rc["passed"] is True and entry["payload"]["spend"] == "sr1"
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "law"))
    from qp.law import use_law
    use_law()
    from acom import receipts as R
    assert R.settle(rc, ev)["ok"] is True


def test_double_settle_rejected(tmp_path):
    L = _ledger(tmp_path)
    L.propose("s10", "test", 500, 1000)
    L.authorize("s10", _grant("s10", 500), {"idem": "s10", "amount": 500}, VERIFY)
    L.settle("s10", 500)
    try:
        L.settle("s10", 500)
        raise SystemExit("double settle accepted")
    except ValueError:
        pass
