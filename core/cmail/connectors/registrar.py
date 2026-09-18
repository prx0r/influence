from __future__ import annotations

import httpx

from .base import Observation
from ..config import settings

RDAP_BOOTSTRAP = "https://data.iana.org/rdap/dns.json"


def _tld_service(tld: str) -> str | None:
    try:
        with httpx.Client(timeout=settings.http_timeout) as client:
            data = client.get(RDAP_BOOTSTRAP).json()
        for svc in data.get("services", []):
            tlds, urls = svc[0], svc[1]
            if tld in [t.lower() for t in tlds] and urls:
                return urls[0].rstrip("/")
    except Exception:
        return None
    return None


def _rdap_lookup(server: str, domain: str) -> dict | None:
    try:
        with httpx.Client(timeout=settings.http_timeout, follow_redirects=True) as client:
            r = client.get(f"{server}/domain/{domain}")
        if r.status_code == 404:
            return {"registered": False}
        if r.status_code != 200:
            return None
        body = r.json()
        registrar = ""
        for ent in body.get("entities", []):
            if "registrar" in [x.lower() for x in ent.get("roles", [])]:
                vcard = ent.get("vcardArray", [None, []])
                for item in vcard[1] if len(vcard) > 1 else []:
                    if item[0] == "fn":
                        registrar = item[3]
                        break
        expiry = next((e["eventDate"] for e in body.get("events", [])
                       if e.get("eventAction") == "expiration"), "")
        return {"registered": True, "registrar": registrar or "unknown",
                "expiry": expiry}
    except Exception:
        return None


class RegistrarConnector:
    """RDAP-based domain registration state. Reports registrar-of-record and
    expiry; never quotes prices (no invented prices) and never claims
    ownership (registration != ours)."""

    kind = "registrar"

    def observe(self, desired: dict) -> Observation:
        domain = (desired.get("domain") or "").strip().lower()
        if not domain or "." not in domain:
            return Observation("MISSING", "No domain selected", executor="HUMAN",
                               human_title="Choose the domain",
                               human_instructions="Pick the canonical domain, then record it in the passport.",
                               estimate_seconds=120, priority=90)
        tld = domain.rsplit(".", 1)[1]
        try:
            server = _tld_service(tld)
            if not server:
                return Observation("UNKNOWN", f"No RDAP service for .{tld}",
                                   observed={"domain": domain}, executor="HUMAN",
                                   human_title=f"Check .{tld} registration manually",
                                   human_instructions=f"RDAP has no booth for .{tld}. Verify registration at the registrar.",
                                   estimate_seconds=120, priority=60)
            info = _rdap_lookup(server, domain)
            if info is None:
                return Observation("UNKNOWN", f"RDAP unavailable for {domain}",
                                   observed={"domain": domain})
            if not info["registered"]:
                return Observation("MISSING", f"{domain} looks unregistered",
                                   observed={"domain": domain}, executor="HUMAN",
                                   human_title=f"Register {domain}",
                                   human_instructions=f"{domain} has no RDAP record. Register it, then re-run reconcile. Price is confirmed at checkout, never quoted here.",
                                   estimate_seconds=300, priority=85)
            return Observation("READY", f"{domain} registered via {info['registrar']}",
                               observed={"domain": domain, "registrar": info["registrar"],
                                         "expiry": info["expiry"]})
        except Exception as exc:
            return Observation("UNKNOWN", f"Registrar check failed: {exc}",
                               observed={"domain": domain})
