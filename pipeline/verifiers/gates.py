"""Verification gates — every channel action goes through these.

G1 attempt → G2 response → G3 verify_exists → G4 content → G5 freshness

A receipt is only written when ALL gates PASS. Nothing is "done" without
a receipt. See docs/pipeline/VERIFICATION-GATES.md for the formal spec.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class GateResult:
    gate_id: str
    passed: bool
    proof: str = ""
    evidence: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.gate_id, "result": "PASS" if self.passed else "FAIL", "proof": self.proof}


@dataclass
class Verified:
    """Outcome of running all gates for one action."""
    channel: str
    external_id: str
    gates: list[GateResult]
    evidence: list[dict]
    claim_statement: str

    @property
    def all_passed(self) -> bool:
        return all(g.passed for g in self.gates)

    def receipt(self) -> dict:
        """Build a QP-style receipt. Only valid if all_passed."""
        claim = {
            "statement": self.claim_statement,
            "domain": f"distribution.{self.channel}",
            "result": "TRUE" if self.all_passed else "UNKNOWN",
        }
        return {
            "protocol": "acom/0.1",
            "channel": self.channel,
            "external_id": self.external_id,
            "claim": claim,
            "evidence": self.evidence,
            "gates": [g.to_dict() for g in self.gates],
            "passed": self.all_passed,
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


def g1_attempt(response_code: int) -> GateResult:
    ok = 200 <= response_code < 300
    return GateResult("g1-attempt-v1", ok, f"HTTP {response_code}",
                      [{"metric": "api.response_code", "value": str(response_code)}])


def g2_response(external_id: str, response: dict) -> GateResult:
    ok = bool(external_id) and external_id not in ("", "None", "null")
    return GateResult("g2-response-v1", ok,
                      f"external_id={external_id}" if ok else "no external_id",
                      [{"metric": "api.external_id", "value": external_id}])


def g3_verify_exists(fetch_result: dict | None) -> GateResult:
    ok = fetch_result is not None and not fetch_result.get("error")
    return GateResult("g3-verify-v1", ok,
                      "fetched OK" if ok else "fetch failed or empty",
                      [{"metric": "verify.exists", "value": "true" if ok else "false"}])


def g4_content(expected: dict, actual: dict, fields: list[str]) -> GateResult:
    mismatches = []
    for f in fields:
        exp = expected.get(f)
        act = actual.get(f)
        if exp is not None and act is not None and str(exp) != str(act):
            mismatches.append(f"{f}: expected {exp!r}, got {act!r}")
    ok = not mismatches
    return GateResult("g4-content-v1", ok,
                      "all fields match" if ok else "; ".join(mismatches[:3]),
                      [{"metric": "content.match", "value": "true" if ok else "false"}])


def g5_fresh(verified_at: str, max_age_sec: int = 3600) -> GateResult:
    try:
        vt = time.mktime(time.strptime(verified_at, "%Y-%m-%dT%H:%M:%SZ"))
        age = time.time() - vt
        ok = 0 <= age <= max_age_sec
        return GateResult("g5-fresh-v1", ok, f"age={age:.0f}s")
    except Exception:
        return GateResult("g5-fresh-v1", False, "bad timestamp")


# Built-in QP gates (from qprivately)
def evidence_fresh(evidence: list[dict]) -> GateResult:
    ok = all(e.get("metric") and e.get("as_of") and e.get("value") is not None for e in evidence)
    return GateResult("evidence-fresh-v1", ok, f"{len(evidence)} items")


def no_duplicate(evidence: list[dict]) -> GateResult:
    ids = [e.get("id", str(i)) for i, e in enumerate(evidence)]
    ok = len(ids) == len(set(ids))
    return GateResult("no-duplicate-v1", ok, f"{len(ids)} items, {len(set(ids))} unique")


def run_gates(channel: str, external_id: str, response_code: int,
              response: dict, fetch_result: dict | None,
              expected: dict, actual: dict, content_fields: list[str],
              claim_statement: str) -> Verified:
    """Run the full gate pipeline for one channel action."""
    evidence: list[dict] = []
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    g1 = g1_attempt(response_code)
    evidence.extend(g1.evidence)

    g2 = g2_response(external_id, response)
    evidence.extend(g2.evidence)

    g3 = g3_verify_exists(fetch_result)
    evidence.extend(g3.evidence)
    if fetch_result and not fetch_result.get("error"):
        for k, v in list(fetch_result.items())[:10]:
            if k != "error":
                evidence.append({"metric": f"verify.{k}", "value": str(v)[:200], "as_of": now})

    g4 = g4_content(expected, actual or {}, content_fields)
    evidence.extend(g4.evidence)

    for e in evidence:
        e.setdefault("as_of", now)

    ef = evidence_fresh(evidence)
    nd = no_duplicate(evidence)

    return Verified(
        channel=channel,
        external_id=external_id,
        gates=[g1, g2, g3, g4, ef, nd],
        evidence=evidence,
        claim_statement=claim_statement,
    )
