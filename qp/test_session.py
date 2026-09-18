"""Tests: sessions, invoice lifecycle, exactly-once mint."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qp.session import SessionStore  # noqa: E402


def _store(tmp_path):
    return SessionStore(str(tmp_path / "s.db"))


def test_lifecycle(tmp_path):
    S = _store(tmp_path)
    s = S.create_session()
    assert s["state"] == "UNFUNDED" and s["capability_token"]
    inv = S.create_invoice(s["session_id"], 1000, "sub-0")
    assert S.observe_payment(inv["invoice_id"], 400, 12) == "PARTIAL"  # underpaid waits
    assert S.observe_payment(inv["invoice_id"], 1000, 3) == "PARTIAL"  # under-confirmed waits
    assert S.observe_payment(inv["invoice_id"], 1000, 10) == "CONFIRMED"
    cap = S.mint_capability(inv["invoice_id"])
    assert S.check_capability(cap["capability_id"], cap["capability_token"]) is True
    assert S.check_capability(cap["capability_id"], "wrong") is False


def test_no_double_mint(tmp_path):
    S = _store(tmp_path)
    s = S.create_session()
    inv = S.create_invoice(s["session_id"], 100, "sub-1")
    S.observe_payment(inv["invoice_id"], 100, 10)
    S.mint_capability(inv["invoice_id"])
    try:
        S.mint_capability(inv["invoice_id"])
        raise SystemExit("double mint accepted")
    except ValueError:
        pass


def test_unconfirmed_never_mints_and_expiry(tmp_path):
    S = _store(tmp_path)
    s = S.create_session()
    inv = S.create_invoice(s["session_id"], 100, "sub-2", ttl_s=-1)
    assert S.observe_payment(inv["invoice_id"], 100, 99) == "EXPIRED"
    try:
        S.mint_capability(inv["invoice_id"])
        raise SystemExit("expired mint accepted")
    except ValueError:
        pass
    try:
        S.create_invoice("sess-nope", 100, "sub-3")
        raise SystemExit("invoice on unknown session accepted")
    except KeyError:
        pass
