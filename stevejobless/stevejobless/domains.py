"""Domain providers — Porkbun + name.com + Cloudflare DNS, one interface.

Ports (Python, stdlib-only): DomainArena's namecom.py (httpx→urllib, same
fail-closed semantics + write-mode guard) and finalbuildsdomain's Porkbun/CF
clients (with corrected `secretapikey` field name per Porkbun docs).
No AGPL code anywhere in this lineage (MIT + own work).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.request import Request, urlopen

UA = {"User-Agent": "stevejobless-domains/0.4"}


class ProviderError(RuntimeError):
    pass


def _post(url: str, payload: dict, headers: dict | None = None, timeout: float = 20) -> Any:
    req = Request(url, data=json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json", **UA, **(headers or {})},
                  method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}")
    except Exception as e:
        body = ""
        if hasattr(e, "read"):
            try:
                body = e.read()[:300].decode(errors="replace")
            except Exception:
                pass
        raise ProviderError(f"POST {url}: {e} {body}")


def _get(url: str, headers: dict | None = None, timeout: float = 20) -> Any:
    req = Request(url, headers={**UA, **(headers or {})}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}")
    except Exception as e:
        raise ProviderError(f"GET {url}: {e}")


def _authed(base: str, api_token: str, method: str, path: str,
            body: dict | None = None, timeout: float = 20) -> Any:
    h = {"Authorization": f"Bearer {api_token}"}
    if method == "GET":
        return _get(base + path, h, timeout)
    req = Request(base + path, data=json.dumps(body or {}).encode(),
                  headers={"Content-Type": "application/json", **UA, **h}, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read() or b"{}")
    except Exception as e:
        detail = ""
        if hasattr(e, "read"):
            try:
                detail = f" :: {e.read()[:400].decode(errors='replace')}"
            except Exception:
                pass
        raise ProviderError(f"{method} {path}: {e}{detail}")
    if isinstance(d, dict) and d.get("success") is False:
        raise ProviderError(f"{method} {path}: {d.get('errors')}")
    return d


class Porkbun:
    """Porkbun v3. Sandbox by default (free, fake credit) — pass sandbox=False
    with live keys only behind the deal state machine + human approval."""

    LIVE = "https://api.porkbun.com/api/json/v3"
    SANDBOX = "https://api-sandbox.porkbun.com/api/json/v3"

    def __init__(self, api_key: str, secret_key: str, sandbox: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base = self.SANDBOX if sandbox else self.LIVE
        self.sandbox = sandbox

    def _p(self, path: str, extra: dict | None = None) -> Any:
        d = _post(self.base + path, {"apikey": self.api_key, "secretapikey": self.secret_key,
                                     **(extra or {})})
        if isinstance(d, dict) and d.get("status") == "ERROR":
            raise ProviderError(f"porkbun {path}: {d.get('message')}")
        return d

    def check(self, domain: str) -> dict:
        d = self._p("/domain/checkDomain", {"domain": domain})
        avail = str(d.get("avail", "")).lower() == "yes"
        return {"domain": domain, "available": avail, "price": d.get("price"),
                "premium": bool(d.get("premium")), "raw": "sandbox" if self.sandbox else "live"}

    def pricing(self, tld: str) -> dict:
        return self._p("/pricing/get", {"tld": tld.lstrip(".")})

    def balance(self) -> Any:
        return self._p("/user/getBalance")

    def register(self, domain: str, *, email: str, nameservers: list[str] | None = None,
                 dry_run: bool = True, idempotency_key: str = "") -> dict:
        body: dict[str, Any] = {"domain": domain, "email": email, "private": "yes"}
        if nameservers:
            body["ns"] = nameservers
        if dry_run:
            body["dryRun"] = "yes"
        if idempotency_key:
            body["idempotencyKey"] = idempotency_key
        return self._p("/domain/create", body)

    def set_nameservers(self, domain: str, nameservers: list[str]) -> dict:
        return self._p("/domain/updateNameservers", {"domain": domain, "ns": nameservers})


class NameCom:
    """name.com Core API. Write guard: mode must be sandbox or production-approved."""

    WRITE_MODES = {"sandbox", "production-approved"}

    def __init__(self, username: str, token: str,
                 base_url: str = "https://api.dev.name.com", mode: str = "sandbox"):
        import base64

        self.base = base_url.rstrip("/")
        self.mode = mode
        self._auth = {"Authorization": "Basic " + base64.b64encode(f"{username}:{token}".encode()).decode()}

    def _req(self, method: str, path: str, body: dict | None = None) -> Any:
        if method == "GET":
            return _get(self.base + path, self._auth)
        req = Request(self.base + path, data=json.dumps(body or {}).encode(),
                      headers={"Content-Type": "application/json", **UA, **self._auth}, method=method)
        try:
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read() or b"{}")
        except Exception as e:
            raise ProviderError(f"name.com {method} {path}: {e}")

    def _write_guard(self):
        if self.mode not in self.WRITE_MODES:
            raise ProviderError(f"write blocked in mode {self.mode!r} (allowed: {sorted(self.WRITE_MODES)})")

    def check(self, domains: list[str]) -> list[dict]:
        d = self._req("POST", "/core/v1/domains:checkAvailability",
                      {"domainNames": domains, "purchaseType": "registration"})
        return d.get("results", d if isinstance(d, list) else [])

    def check_fail_closed(self, domain: str) -> dict:
        results = self.check([domain])
        entry = next((r for r in results
                      if (r.get("domainName") or r.get("domain", "")).lower() == domain.lower()), None)
        if entry is None:
            raise ProviderError(f"no availability response for {domain}")
        if "purchasable" not in entry:
            raise ProviderError(f"missing 'purchasable' for {domain}")
        if entry.get("purchaseType") != "registration":
            raise ProviderError(f"unexpected purchaseType for {domain}")
        return entry

    def pricing(self, domain: str) -> dict:
        return self._req("GET", f"/core/v1/domains/{domain}:getPricing")

    def register(self, payload: dict, idempotency_key: str) -> dict:
        self._write_guard()
        req = Request(self.base + "/core/v1/domains", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "X-Idempotency-Key": idempotency_key,
                               **UA, **self._auth}, method="POST")
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"{}")
        except Exception as e:
            raise ProviderError(f"name.com register {payload.get('domainName')}: {e}")

    def create_dns(self, domain: str, host: str, rtype: str, answer: str, ttl: int = 300) -> dict:
        self._write_guard()
        return self._req("POST", f"/core/v1/domains/{domain}/records",
                         {"host": host, "type": rtype, "answer": answer, "ttl": max(300, ttl)})


class CloudflareDNS:
    """Post-registrar wiring: zone → records → Email Routing → worker. Uses the
    operator Cloudflare token (env CLOUDFLARE_API_TOKEN), never per-business keys."""

    BASE = "https://api.cloudflare.com/client/v4"

    def __init__(self, api_token: str, account_id: str):
        self.token = api_token
        self.account = account_id

    def _api(self, method: str, path: str, body: dict | None = None) -> Any:
        return _authed(self.BASE, self.token, method, path, body)

    def find_zone(self, domain: str) -> dict | None:
        d = self._api("GET", f"/zones?name={domain}")
        return (d.get("result") or [None])[0]

    def create_zone(self, domain: str) -> dict:
        d = self._api("POST", "/zones", {"name": domain, "account": {"id": self.account}})
        return d.get("result", {})

    def enable_routing(self, zone_id: str) -> dict:
        # Current API: POST .../email/routing/dns (adds CF MX). /enable is deprecated.
        return self._api("POST", f"/zones/{zone_id}/email/routing/dns", {})

    def add_subdomain_mx(self, zone_id: str, sub: str) -> list[dict]:
        """Subdomain mail without touching root MX (root stays on Zoho etc.).
        Verified live 2026-09-10 on tantrafiles.xyz."""
        out = []
        for prio, host in ((63, "route1.mx.cloudflare.net."), (17, "route2.mx.cloudflare.net."),
                           (55, "route3.mx.cloudflare.net.")):
            out.append(self._api("POST", f"/zones/{zone_id}/dns_records",
                                 {"type": "MX", "name": sub, "content": host,
                                  "priority": prio, "ttl": 1}))
        return out

    def route_address_to_worker(self, zone_id: str, address: str, worker_name: str,
                                rule_name: str = "cmail") -> dict:
        d = self._api("POST", f"/zones/{zone_id}/email/routing/rules", {
            "name": rule_name, "enabled": True, "priority": 0,
            "actions": [{"type": "worker", "value": [worker_name]}],
            "matchers": [{"type": "literal", "field": "to", "value": address}],
        })
        return d.get("result", d)

    def catchall_to_worker(self, zone_id: str, worker_name: str) -> dict:
        # Current API: PUT .../rules/catch_all (not POST /rules).
        d = self._api("PUT", f"/zones/{zone_id}/email/routing/rules/catch_all", {
            "name": "cmail catch-all", "enabled": True,
            "actions": [{"type": "worker", "value": [worker_name]}],
            "matchers": [{"type": "all"}],
        })
        return d.get("result", d)


def idempotency_key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# API-excluded from programmatic registration (dashboard-only). Keep in sync
# with https://developers.cloudflare.com/api/resources/registrar/
CF_API_EXCLUDED_TLDS = {"giving", "mom", "inc", "lol", "sh", "link", "cc", "new"}


class CloudflareRegistrar:
    """Cloudflare Registrar API (beta): search/check/register at cost.
    No sandbox exists — reads are free, registration is live money, so the
    deal machine gates writes behind approval + DOMAINS_ALLOW_LIVE."""

    def __init__(self, api_token: str, account_id: str):
        self.token = api_token
        self.account = account_id

    def _api(self, method: str, path: str, body: dict | None = None) -> Any:
        return _authed("https://api.cloudflare.com/client/v4", self.token, method,
                       f"/accounts/{self.account}/registrar{path}", body)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        import urllib.parse

        d = self._api("GET", f"/domain-search?q={urllib.parse.quote(query)}&limit={limit}")
        return (d.get("result") or {}).get("domains", [])

    def check(self, domain: str) -> dict:
        tld = domain.rsplit(".", 1)[-1].lower()
        if tld in CF_API_EXCLUDED_TLDS:
            return {"domain": domain, "available": False, "price": None,
                    "reason": "extension_not_supported_via_api — dashboard or Porkbun/Name.com, then NS-move"}
        d = self._api("POST", "/domain-check", {"domains": [domain]})
        results = (d.get("result") or {}).get("domains", []) or []
        r = next((x for x in results if x.get("name", "").lower() == domain.lower()), None)
        if r is None:
            raise ProviderError(f"no check response for {domain}")
        if r.get("tier") == "premium":
            return {"domain": domain, "available": False, "price": None,
                    "reason": "premium tier not supported via API"}
        pricing = r.get("pricing") or {}
        price = pricing.get("registration_cost") or pricing.get("registration") or pricing.get("register")
        return {"domain": domain, "available": bool(r.get("registrable")),
                "price": float(price) if price is not None else None,
                "premium": False, "reason": r.get("reason")}

    def register(self, domain: str, *, allow_live: bool) -> dict:
        if not allow_live:
            raise ProviderError("Cloudflare has no sandbox — live registration needs DOMAINS_ALLOW_LIVE=1 + approval")
        d = self._api("POST", "/registrations", {"domain_name": domain})
        return d.get("result", d)

    def registration_status(self, domain: str) -> dict:
        d = self._api("GET", f"/registrations/{domain}")
        return d.get("result", d)

    def list_registrations(self) -> list[dict]:
        d = self._api("GET", "/registrations")
        res = d.get("result")
        return res if isinstance(res, list) else []
