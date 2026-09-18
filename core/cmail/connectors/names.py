from __future__ import annotations

import os
from typing import Any

import httpx

from .base import Observation
from ..config import settings

# Live name-intelligence service (cmail's checker worker). We CALL it —
# verify, prices, handles, claim kit — never copy it. Any network failure
# is UNKNOWN, never a verdict.
CHECKER = os.getenv("NAMES_CHECKER_URL",
                    "https://domainnamechecker.tradesprior.workers.dev")


def _get(path: str) -> tuple[int | None, Any]:
    try:
        with httpx.Client(timeout=settings.http_timeout) as client:
            r = client.get(CHECKER + path)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None
    except Exception:
        return None, None


class NamesConnector:
    """Check-a-name-everywhere via the live checker: RDAP/DNS verdict,
    cheapest-registrar compare, handle namespace scan. Read-only."""

    kind = "names"

    def observe(self, desired: dict) -> Observation:
        domain = (desired.get("domain") or "").strip().lower()
        name = (desired.get("name") or "").strip().lower()
        if not domain and not name:
            return Observation("MISSING", "No name to check", executor="HUMAN",
                               human_title="Pick a name",
                               human_instructions="Give the idea a name first (docs/NAMING.md), then check it everywhere.",
                               estimate_seconds=120, priority=80)
        target = domain or f"{name}.dev"
        code, verdict = _get(f"/api/verify/{target}")
        if code is None:
            return Observation("UNKNOWN", f"Name-intel unreachable for {target} (checker down?)",
                               observed={"target": target})
        reg = verdict.get("registration", {}) if isinstance(verdict, dict) else {}
        status = str(reg.get("status", "unknown")).lower()
        if status == "taken":
            return Observation("BLOCKED", f"{target} is taken (authoritative)",
                               observed={"target": target, "verdict": verdict},
                               executor="HUMAN",
                               human_title=f"Pick another name ({target} taken)",
                               human_instructions="The registry says taken. Generate more candidates (POST /api/mine) and check again.",
                               estimate_seconds=180, priority=70)
        if status in ("available", "unregistered"):
            code2, prices = _get(f"/api/registrar/{target}")
            observed: dict[str, Any] = {"target": target, "verdict": verdict}
            if code2 == 200 and isinstance(prices, dict):
                observed["prices"] = prices
            return Observation("MISSING", f"{target} looks free — human buys (see docs/BUY-DOMAIN.md)",
                               observed=observed, executor="HUMAN",
                               human_title=f"Buy {target}",
                               human_instructions="Review the registrar compare, buy at the cheapest link, then re-run reconcile to verify + wire.",
                               estimate_seconds=600, priority=90)
        return Observation("UNKNOWN", f"{target}: verdict {status or 'unreadable'} — claimability unproved",
                           observed={"target": target, "verdict": verdict})
