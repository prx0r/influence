"""Tests: disclosure manifests + PII scan gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qp.disclosure import check_public, manifest, scan  # noqa: E402


def _receipt(**kw):
    r = {"id": "receipt:abc", "gates": [], "evidence_root": "root:1"}
    r.update(kw)
    return r


def test_clean_passes():
    m = manifest("receipt:abc", "root:1", "ANON_CORE")
    assert check_public(_receipt(), m)["ok"] is True


def test_pii_fails():
    assert "email address present" in scan(_receipt(note="mail bob@example.com"))
    assert "phone-like number present" in scan(_receipt(note="call +1 415 555 0132 now"))
    assert "secret-looking material present" in scan(_receipt(key="ghp_abcdefghij1234567890"))
    m = manifest("receipt:abc", "root:1", "ANON_CORE")
    assert check_public(_receipt(note="bob@example.com"), m)["ok"] is False


def test_binding_enforced():
    m = manifest("receipt:other", "root:1", "ANON_CORE")
    rep = check_public(_receipt(), m)
    assert rep["ok"] is False and rep["bound"] is False


def test_manifest_records_bridges():
    m = manifest("receipt:abc", "root:1", "IDENTITY_BRIDGED",
                 [{"provider": "telnyx", "fields_disclosed": ["number"],
                   "identity_required": True}])
    assert m["identity_bridges"] == ["telnyx"] and m["manifest_root"].startswith("sha256:")
