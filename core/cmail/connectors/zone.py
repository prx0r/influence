from __future__ import annotations

import os

import httpx

from .base import Observation
from ..config import settings

DOH = "https://cloudflare-dns.com/dns-query"


def _doh(domain: str, qtype: str) -> list[str] | None:
    """DNS answers over HTTPS. Returns None on network failure (UNKNOWN),
    never raises."""
    try:
        with httpx.Client(timeout=settings.http_timeout) as client:
            r = client.get(DOH, params={"name": domain, "type": qtype},
                           headers={"accept": "application/dns-json"})
        if r.status_code != 200:
            return None
        answers = r.json().get("Answer") or []
        return [a.get("data", "") for a in answers]
    except Exception:
        return None


class ZoneConnector:
    """Nameserver placement. With a Cloudflare token present (env only, never
    printed) it confirms the zone; without it, it reports observed NS hosts
    and asks a human for the move."""

    kind = "zone"

    def observe(self, desired: dict) -> Observation:
        domain = (desired.get("domain") or "").strip().lower()
        if not domain or "." not in domain:
            return Observation("MISSING", "No domain for zone check", executor="HUMAN",
                               human_title="Choose the domain",
                               human_instructions="Record the canonical domain first.",
                               estimate_seconds=60, priority=80)
        ns = _doh(domain, "NS")
        if ns is None:
            return Observation("UNKNOWN", f"NS lookup unavailable for {domain}",
                               observed={"domain": domain})
        hosts = sorted({h.rstrip(".").lower() for h in ns})
        on_cf = any("cloudflare" in h for h in hosts)
        if os.getenv("CF_API_TOKEN"):
            # Token presence only; the call carries no secrets in output.
            try:
                with httpx.Client(timeout=settings.http_timeout) as client:
                    r = client.get("https://api.cloudflare.com/client/v4/zones",
                                   params={"name": domain},
                                   headers={"Authorization": "Bearer " + os.getenv("CF_API_TOKEN", "")})
                zones = (r.json().get("result") or []) if r.status_code == 200 else []
                if zones and zones[0].get("status") == "active":
                    return Observation("READY", f"{domain} zone active",
                                       observed={"domain": domain, "ns": hosts})
            except Exception:
                pass
            return Observation("UNKNOWN", f"Zone status unverifiable for {domain}",
                               observed={"domain": domain, "ns": hosts})
        if on_cf:
            return Observation("READY", f"{domain} NS on Cloudflare",
                               observed={"domain": domain, "ns": hosts})
        if not hosts:
            return Observation("MISSING", f"No NS records for {domain}", executor="HUMAN",
                               human_title=f"Delegate {domain}",
                               human_instructions=f"{domain} has no nameservers. Delegate it at the registrar first.",
                               estimate_seconds=300, priority=85)
        return Observation("MISSING", f"{domain} NS not on Cloudflare ({hosts[0]})",
                           observed={"domain": domain, "ns": hosts}, executor="HUMAN",
                           human_title=f"Move NS for {domain} to Cloudflare",
                           human_instructions="Change nameservers at the registrar to the assigned Cloudflare pair, then re-run reconcile. I verify automatically.",
                           estimate_seconds=300, priority=80)


class MailConnector:
    """Mailbox readiness via MX records (DoH, no creds). READY means mail can
    route; it never means a message was received (attempt is not observation)."""

    kind = "mail"

    def observe(self, desired: dict) -> Observation:
        domain = (desired.get("domain") or "").strip().lower()
        if not domain or "." not in domain:
            return Observation("MISSING", "No domain for mail check", executor="HUMAN",
                               human_title="Choose the domain",
                               human_instructions="Record the canonical domain first.",
                               estimate_seconds=60, priority=80)
        mx = _doh(domain, "MX")
        if mx is None:
            return Observation("UNKNOWN", f"MX lookup unavailable for {domain}",
                               observed={"domain": domain})
        hosts = sorted({m.split()[-1].rstrip(".").lower() for m in mx if m})
        want = (desired.get("mx_host") or "").strip().lower()
        if not hosts:
            return Observation("MISSING", f"No MX for {domain}", executor="HUMAN",
                               human_title=f"Set up mail for {domain}",
                               human_instructions=f"Add MX records for {domain} (Email Routing or provider), then re-run reconcile.",
                               estimate_seconds=300, priority=75)
        if want and not any(want in h for h in hosts):
            return Observation("MISSING", f"{domain} MX not at {want}",
                               observed={"domain": domain, "mx": hosts}, executor="HUMAN",
                               human_title=f"Point MX for {domain} at {want}",
                               human_instructions=f"Current MX: {', '.join(hosts)}. Move them, then re-run reconcile.",
                               estimate_seconds=300, priority=75)
        return Observation("READY", f"{domain} mail routes ({hosts[0]})",
                           observed={"domain": domain, "mx": hosts})
