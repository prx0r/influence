"""Authority grants ported from pmail authority/grantex patterns (ISC, prx0r/pmail).
Grant binds issuer/subject/action/payload-hash with expiry, nonce, max_uses under Ed25519.
Server reconstructs the proposal and requires byte-equal payload_hash before acting."""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass

from nacl.signing import SigningKey, VerifyKey


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def payload_hash(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical(payload)).hexdigest()


@dataclass
class Grant:
    issuer: str
    subject: str
    action: str
    payload_hash: str
    issued_at: int
    expires_at: int
    nonce: str
    max_uses: int
    signature: str = ""

    def body(self) -> dict:
        return {"issuer": self.issuer, "subject": self.subject, "action": self.action,
                "payload_hash": self.payload_hash, "issued_at": self.issued_at,
                "expires_at": self.expires_at, "nonce": self.nonce, "max_uses": self.max_uses}


def issue(action: str, payload: dict, subject: str, issuer: str, key: SigningKey,
          ttl_s: int = 600, max_uses: int = 1) -> Grant:
    now = int(time.time())
    g = Grant(issuer=issuer, subject=subject, action=action, payload_hash=payload_hash(payload),
              issued_at=now, expires_at=now + ttl_s, nonce=secrets.token_hex(16), max_uses=max_uses)
    g.signature = key.sign(canonical(g.body())).signature.hex()
    return g


def validate(g: Grant, action: str, payload: dict, verify: VerifyKey, uses: int = 0) -> tuple[bool, str]:
    if g.action != action:
        return False, "action mismatch"
    if g.payload_hash != payload_hash(payload):
        return False, "payload mismatch"
    now = int(time.time())
    if now > g.expires_at:
        return False, "expired"
    if uses >= g.max_uses:
        return False, "uses exhausted"
    try:
        verify.verify(canonical(g.body()), bytes.fromhex(g.signature))
    except Exception:
        return False, "bad signature"
    return True, "ok"
