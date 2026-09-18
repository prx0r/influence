"""Disclosure manifests: what a receipt reveals, stated plainly and hashed.
Public receipts carry commitments, never raw PII. scan() fails any payload
containing emails, phones, secret-looking tokens, or private keys. Narrow
claims only: absence of a log line is never proof of non-collection."""
from __future__ import annotations

import hashlib
import json
import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\+?\d[\d .\-()]{7,}\d")
SECRET = re.compile(r"(ghp_|cfat_|cfut_|sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")


def scan(obj: dict) -> list[str]:
    """Return violations found in the canonical JSON of obj (empty = clean)."""
    text = json.dumps(obj, sort_keys=True)
    bad = []
    if EMAIL.search(text):
        bad.append("email address present")
    if PHONE.search(text):
        bad.append("phone-like number present")
    if SECRET.search(text):
        bad.append("secret-looking material present")
    return bad


def manifest(receipt_id: str, evidence_root: str, privacy_class: str,
             providers: list[dict] | None = None, payment_rail: str = "",
             network_path: list[str] | None = None) -> dict:
    """Build + hash a disclosure manifest. Providers list what each
    dependency saw: [{provider, fields_disclosed, identity_required}]."""
    m = {"receipt_id": receipt_id, "evidence_root": evidence_root,
         "pmail_collected": [], "privacy_class": privacy_class,
         "providers": providers or [], "payment_rail": payment_rail,
         "network_path": network_path or [], "identity_bridges": [
             p["provider"] for p in (providers or []) if p.get("identity_required")]}
    m["manifest_root"] = "sha256:" + hashlib.sha256(
        json.dumps(m, sort_keys=True).encode()).hexdigest()
    return m


def check_public(receipt: dict, manifest_obj: dict) -> dict:
    """Gate for anything public: PII scan clean + manifest bound to receipt."""
    violations = scan(receipt)
    bound = manifest_obj.get("receipt_id") == receipt.get("id")
    ok = not violations and bound
    return {"ok": ok, "violations": violations, "bound": bound,
            "manifest_root": manifest_obj.get("manifest_root", "")}
