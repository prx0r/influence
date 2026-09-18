"""Contract tests for registrar/zone/mail/number connectors + bridge selection."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cmail.connectors import CONNECTORS  # noqa: E402
from core.cmail.connectors.phone import select_bridge  # noqa: E402

VALID = {"READY", "MISSING", "BLOCKED", "UNKNOWN", "ERROR"}


def test_all_registered():
    for kind in ("registrar", "zone", "mail", "number"):
        assert kind in CONNECTORS, kind


def test_never_raises_and_valid():
    cases = {
        "registrar": [{}, {"domain": ""}, {"domain": "no-tld"}, {"domain": "example.com"}],
        "zone": [{}, {"domain": ""}, {"domain": "example.com"}],
        "mail": [{}, {"domain": ""}, {"domain": "example.com"},
                 {"domain": "example.com", "mx_host": "example.net"}],
        "number": [{}, {"capabilities": ["sms_in"]}, {"capabilities": ["voice_out"]},
                   {"capabilities": ["sms_in"], "resource_ref": "pn_123"},
                   {"capabilities": ["sms_in"], "max_class": "bogus"}],
    }
    for kind, desireds in cases.items():
        for d in desireds:
            ob = CONNECTORS[kind].observe(d)  # must not raise
            assert ob.status in VALID, (kind, d, ob.status)
            assert ob.executor in ("AUTO", "HUMAN"), (kind, d)
            if ob.executor == "HUMAN":
                assert ob.human_title, (kind, d)


def test_no_prices_quoted():
    ob = CONNECTORS["registrar"].observe({"domain": "example.com"})
    blob = (ob.message + str(ob.observed)).lower()
    assert "$" not in blob and "price" not in blob or "never quoted" in blob


def test_select_hard_filter():
    sms = select_bridge(["sms_in"])
    assert any(e["provider"] == "silentlink" for e in sms["eligible"])
    assert all(e["provider"] != "telnyx" for e in sms["eligible"])  # KYC rejected
    voice = select_bridge(["voice_out"])
    assert voice["eligible"] == []  # nothing proven TRUE
    assert any(r["provider"] == "pikasim" for r in voice["rejected"])
    strict = select_bridge(["sms_in"], max_class="ANON_CORE")
    assert strict["eligible"] == []  # bridges degrade below ANON_CORE
    loose = select_bridge(["sms_in"], max_class="IDENTITY_BRIDGED")
    assert len(loose["eligible"]) >= len(sms["eligible"])  # monotonic


def test_ref_stays_unknown():
    ob = CONNECTORS["number"].observe({"capabilities": ["sms_in"], "resource_ref": "pn_1"})
    assert ob.status == "UNKNOWN"  # purchase is not proof
