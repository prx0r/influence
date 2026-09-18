"""Tests for influencer passport shape + stage derivation."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cmail.influencer import derive_stage, influencer_passport


def test_passport_chain_order_and_shape():
    p = influencer_passport("novaink", "novaink.dev")
    assert [r["key"] for r in p["resources"]] == [
        "name", "handles", "domain", "registrar", "zone", "mailbox", "number", "social:x", "content"]
    assert all(r["kind"] and r["label"] and r["desired"] for r in p["resources"])
    kinds = {r["key"]: r["kind"] for r in p["resources"]}
    assert kinds["domain"] == "domain" and kinds["zone"] == "website" and kinds["social:x"] == "social"
    assert kinds["registrar"] == "registrar" and kinds["mailbox"] == "mail" and kinds["number"] == "number"


def test_stage_derivation():
    assert derive_stage({}) == "untouched"
    assert derive_stage({"name": "READY"}) == "name-only"
    assert derive_stage({"name": "READY", "domain": "READY"}) == "domain-owned"
    assert derive_stage({"domain": "READY", "mailbox": "READY"}) == "wired-needs-content"
    assert derive_stage({"content": "READY"}) == "live"
