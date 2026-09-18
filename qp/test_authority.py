"""Tests: grant forgery/replay/expiry + journal idempotency and illegal transitions."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from nacl.signing import SigningKey

from qp.authority import issue, validate
from qp.journal import Journal


def test_grant_roundtrip_and_bindings():
    key = SigningKey.generate()
    payload = {"task": "A-1", "digit": "7"}
    g = issue("task.decide", payload, "op:1", "auth:local", key)
    ok, _ = validate(g, "task.decide", payload, key.verify_key)
    assert ok
    ok, why = validate(g, "other.action", payload, key.verify_key)
    assert not ok and why == "action mismatch"
    ok, why = validate(g, "task.decide", {"task": "A-1", "digit": "1"}, key.verify_key)
    assert not ok and why == "payload mismatch"
    ok, why = validate(g, "task.decide", payload, key.verify_key, uses=1)
    assert not ok and why == "uses exhausted"


def test_grant_forgery_and_expiry():
    key = SigningKey.generate()
    evil = SigningKey.generate()
    payload = {"task": "A-1"}
    g = issue("task.decide", payload, "op:1", "auth:local", key, ttl_s=-1)
    ok, why = validate(g, "task.decide", payload, key.verify_key)
    assert not ok and why == "expired"
    g2 = issue("task.decide", payload, "op:1", "auth:local", key)
    ok, why = validate(g2, "task.decide", payload, evil.verify_key)
    assert not ok and why == "bad signature"


def test_journal_idempotent_and_guarded():
    j = Journal(tempfile.mktemp(suffix=".db"))
    assert j.propose("e1", "task.decide") == "PROPOSED"
    assert j.propose("e1", "task.decide") == "PROPOSED"  # no duplicate, same state
    assert j.transition("e1", "AUTHORIZED", grant_ref="g1") == "AUTHORIZED"
    with pytest.raises(ValueError):
        j.transition("e1", "PROVEN_TRUE")  # must go through EXECUTING
    assert j.transition("e1", "EXECUTING") == "EXECUTING"
    assert j.transition("e1", "PROVEN_TRUE") == "PROVEN_TRUE"
    with pytest.raises(ValueError):
        j.transition("e1", "EXECUTING")  # terminal is final
    with pytest.raises(KeyError):
        j.transition("nope", "AUTHORIZED")
