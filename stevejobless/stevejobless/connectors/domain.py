from __future__ import annotations

import socket
import httpx

from .base import Observation
from ..config import settings


class DomainConnector:
    kind = "domain"

    def observe(self, desired: dict) -> Observation:
        domain = desired.get("domain")
        if not domain:
            return Observation("MISSING", "No domain selected", executor="HUMAN",
                               human_title="Choose the product domain",
                               human_instructions="Register or select the canonical domain, then put it in the Studio Passport.",
                               estimate_seconds=120, priority=95)
        try:
            ips = sorted({x[4][0] for x in socket.getaddrinfo(domain, 443, proto=socket.IPPROTO_TCP)})
        except Exception as exc:
            return Observation("MISSING", f"DNS does not currently resolve: {exc}", executor="HUMAN",
                               human_title=f"Point DNS for {domain}",
                               human_instructions=f"Configure DNS for {domain}. Steve will verify resolution automatically.",
                               estimate_seconds=120, priority=90)
        return Observation("READY", f"{domain} resolves", observed={"domain": domain, "ips": ips[:6]})


class WebsiteConnector:
    kind = "website"

    def observe(self, desired: dict) -> Observation:
        url = desired.get("url")
        if not url:
            return Observation("MISSING", "No production URL configured", executor="AUTO",
                               human_title="Deploy production website",
                               human_instructions="Connect a deployment provider or deploy the website, then add its URL to the passport.",
                               estimate_seconds=180, priority=70)
        try:
            with httpx.Client(timeout=settings.http_timeout, follow_redirects=True) as client:
                r = client.get(url)
            status = "READY" if r.status_code < 500 else "ERROR"
            return Observation(status, f"Production returned HTTP {r.status_code}", observed={"url": str(r.url), "http_status": r.status_code})
        except Exception as exc:
            return Observation("UNKNOWN", f"Production check unavailable: {exc}", observed={"url": url})
