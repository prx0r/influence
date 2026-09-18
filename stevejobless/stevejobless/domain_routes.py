"""Domain routes — check → prepare → approve → register → wire.

One-click buy-all lives here, behind the same rules as money everywhere:
no blind buys (fail-closed checks), no drift (recheck at register),
no surprises (budget cap), one-time approval tokens, full receipts.
Sandbox/fixture by default; live needs DOMAINS_ALLOW_LIVE=1 + approval.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import domains as prov
from .domain_deals import DealError, DomainDeal, check_approval, mint_approval, price_ok, transition
from .vault import CredentialVault

router = APIRouter(prefix="/api/domains", tags=["domains"])

CHECKER = os.getenv("DOMAIN_CHECKER_URL", "https://domainnamechecker.tradesprior.workers.dev")


def _db():
    from .db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _live() -> bool:
    return os.getenv("DOMAINS_ALLOW_LIVE", "") == "1"


def _cf_reg(db: Session) -> prov.CloudflareRegistrar:
    token, acct = os.getenv("CLOUDFLARE_API_TOKEN", ""), os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    if not (token and acct):
        raise HTTPException(409, "no Cloudflare operator token on server")
    return prov.CloudflareRegistrar(token, acct)


def _porkbun(db: Session) -> prov.Porkbun:
    v = CredentialVault(db)
    key, secret = v.get_credential("studio", "porkbun", "api_key"), v.get_credential("studio", "porkbun", "secret_key")
    if not (key and secret):
        raise HTTPException(409, "no porkbun creds — save via /api/domains/creds (sandbox key is free)")
    sandbox = (v.get_credential("studio", "porkbun", "sandbox") or "1") == "1"
    return prov.Porkbun(key, secret, sandbox=sandbox and not _live())


def _namecom(db: Session) -> prov.NameCom:
    v = CredentialVault(db)
    user, token = v.get_credential("studio", "namecom", "username"), v.get_credential("studio", "namecom", "token")
    if not (user and token):
        raise HTTPException(409, "no name.com creds — save via /api/domains/creds")
    base = v.get_credential("studio", "namecom", "base_url") or "https://api.dev.name.com"
    mode = "sandbox" if "dev." in base and not _live() else ("production-approved" if _live() else "production-readonly")
    return prov.NameCom(user, token, base, mode)


def _cf() -> prov.CloudflareDNS:
    token, acct = os.getenv("CLOUDFLARE_API_TOKEN", ""), os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    if not (token and acct):
        raise HTTPException(409, "no Cloudflare operator token on server")
    return prov.CloudflareDNS(token, acct)


def _deal(db: Session, deal_id: int) -> DomainDeal:
    d = db.scalar(select(DomainDeal).where(DomainDeal.id == deal_id))
    if not d:
        raise HTTPException(404, "no such deal")
    return d


# ---- creds + providers ----

class Creds(BaseModel):
    porkbun_key: str | None = None
    porkbun_secret: str | None = None
    namecom_user: str | None = None
    namecom_token: str | None = None
    namecom_base_url: str | None = None


@router.post("/creds")
def save_creds(body: Creds, db: Session = Depends(_db)):
    v = CredentialVault(db)
    if body.porkbun_key and body.porkbun_secret:
        v.set_credential("studio", "porkbun", "api_key", body.porkbun_key)
        v.set_credential("studio", "porkbun", "secret_key", body.porkbun_secret)
        v.set_credential("studio", "porkbun", "sandbox", "0" if _live() else "1")
    if body.namecom_user and body.namecom_token:
        v.set_credential("studio", "namecom", "username", body.namecom_user)
        v.set_credential("studio", "namecom", "token", body.namecom_token)
    if body.namecom_base_url:
        v.set_credential("studio", "namecom", "base_url", body.namecom_base_url)
    return {"ok": True, "live": _live()}


@router.get("/providers")
def providers(db: Session = Depends(_db)):
    v = CredentialVault(db)
    return {
        "porkbun": {"configured": bool(v.get_credential("studio", "porkbun", "api_key")),
                    "sandbox": (v.get_credential("studio", "porkbun", "sandbox") or "1") == "1"},
        "namecom": {"configured": bool(v.get_credential("studio", "namecom", "username"))},
        "cloudflare": {"configured": bool(os.getenv("CLOUDFLARE_API_TOKEN", ""))},
        "live": _live(),
    }


# ---- check (checker pre-filter + provider price) ----

@router.get("/check")
def check(domain: str, provider: str = "porkbun", db: Session = Depends(_db)):
    import json as _json
    from urllib.request import Request, urlopen

    pre: dict = {}
    try:
        req = Request(f"{CHECKER}/api/verify/{domain}", headers={"User-Agent": "stevejobless-domains/0.4"})
        with urlopen(req, timeout=15) as resp:
            v = _json.loads(resp.read())
            pre = {"status": v.get("registration", {}).get("status"),
                   "confidence": v.get("registration", {}).get("confidence")}
    except Exception as e:
        pre = {"status": "unknown", "error": str(e)[:100]}
    try:
        if provider == "porkbun":
            q = _porkbun(db).check(domain)
            price = float(str(q.get("price", "0")).replace("$", "") or 0)
        elif provider == "cloudflare":
            q = _cf_reg(db).check(domain)
            price = float(q.get("price") or 0)
        else:
            entry = _namecom(db).check_fail_closed(domain)
            price = float(entry.get("purchasePrice", 0) or 0)
            q = {"available": bool(entry.get("purchasable")), "premium": bool(entry.get("premium"))}
    except HTTPException:
        raise
    except prov.ProviderError as e:
        return {"domain": domain, "prefilter": pre, "provider": provider, "error": str(e)[:200]}
    return {"domain": domain, "prefilter": pre, "provider": provider,
            "available": q.get("available"), "price": price, "premium": q.get("premium"),
            "reason": q.get("reason")}


# ---- deal lifecycle ----

class Prepare(BaseModel):
    domain: str
    provider: str = "auto"  # auto|cloudflare|porkbun|namecom — auto buys cheapest under cap
    max_price: float = 25.0
    registrant_email: str = ""


def _quote(provider: str, domain: str, db: Session) -> dict:
    """Cheapest-signal quote from one provider. Raises HTTPException if unusable."""
    c = check(domain, provider, db)
    if c.get("error"):
        raise HTTPException(502, c["error"])
    return c


@router.post("/prepare")
def prepare(body: Prepare, db: Session = Depends(_db)):
    if body.provider not in ("auto", "cloudflare", "porkbun", "namecom"):
        raise HTTPException(400, "provider must be auto|cloudflare|porkbun|namecom")
    # Cloudflare-first: at-cost + already home. Others compete / cover exclusions.
    candidates = ["cloudflare", "porkbun", "namecom"] if body.provider == "auto" else [body.provider]
    quotes = []
    for prov_name in candidates:
        try:
            q = _quote(prov_name, body.domain, db)
            if q.get("available") and q.get("price") is not None:
                quotes.append((float(q["price"]), prov_name, q))
        except HTTPException:
            continue  # unconfigured provider is skipped, not fatal
    if not quotes:
        raise HTTPException(409, f"{body.domain}: no provider reports available+priced")
    quotes.sort(key=lambda t: t[0])
    price, chosen, c = quotes[0]
    ok, why = price_ok(price, price, body.max_price)
    if not ok:
        cheapest = ", ".join(f"{p}=${pr}" for pr, p, _ in quotes)
        raise HTTPException(409, f"{why} (cheapest: {cheapest})")
    deal = DomainDeal(domain=body.domain.lower(), provider=chosen, max_price=body.max_price,
                      quoted_price=price,
                      result={"registrant_email": body.registrant_email, "prefilter": c.get("prefilter"),
                              "all_quotes": {p: pr for pr, p, _ in quotes}})
    db.add(deal)
    db.flush()
    try:
        transition(deal, "PREPARED", f"available at {price} via {chosen} (cheapest of {len(quotes)})")
    except DealError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True, "deal_id": deal.id, "domain": deal.domain, "price": deal.quoted_price,
            "provider": chosen, "status": deal.status}


@router.post("/{deal_id}/approve")
def approve(deal_id: int, db: Session = Depends(_db)):
    deal = _deal(db, deal_id)
    try:
        raw = mint_approval(deal)
        transition(deal, "APPROVED", "human approved spend")
    except DealError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True, "approval_token": raw,
            "warning": "one-time token — register within the hour, price rechecked at execution"}


class Register(BaseModel):
    approval_token: str


@router.post("/{deal_id}/register")
def register(deal_id: int, body: Register, db: Session = Depends(_db)):
    deal = _deal(db, deal_id)
    try:
        check_approval(deal, body.approval_token)
    except DealError as e:
        raise HTTPException(403, str(e))
    email = (deal.result or {}).get("registrant_email") or os.getenv("DEFAULT_REGISTRANT_EMAIL", "")
    if not email:
        raise HTTPException(400, "registrant_email required (was empty at prepare)")
    try:
        if deal.provider == "cloudflare":
            cf = _cf_reg(db)
            fresh = cf.check(deal.domain)
            ok, why = price_ok(fresh.get("price"), deal.quoted_price, deal.max_price)
            if not ok or not fresh.get("available"):
                transition(deal, "FAILED", why if not ok else "went unavailable since prepare")
                db.commit()
                raise HTTPException(409, f"recheck failed: {why if not ok else 'unavailable'}")
            res = cf.register(deal.domain, allow_live=_live())
            deal.result = {**deal.result, "order": str(res)[:500]}
        elif deal.provider == "porkbun":
            p = _porkbun(db)
            fresh = p.check(deal.domain)
            ok, why = price_ok(float(str(fresh.get("price", "0")).replace("$", "") or 0),
                               deal.quoted_price, deal.max_price)
            if not ok or not fresh.get("available"):
                transition(deal, "FAILED", why if not ok else "went unavailable since prepare")
                db.commit()
                raise HTTPException(409, f"recheck failed: {why if not ok else 'unavailable'}")
            res = p.register(deal.domain, email=email,
                             dry_run=not _live(),
                             idempotency_key=prov.idempotency_key(str(deal.id), deal.domain, "register"))
        else:
            n = _namecom(db)
            entry = n.check_fail_closed(deal.domain)
            ok, why = price_ok(float(entry.get("purchasePrice", 0) or 0), deal.quoted_price, deal.max_price)
            if not ok or not entry.get("purchasable"):
                transition(deal, "FAILED", why if not ok else "went unavailable since prepare")
                db.commit()
                raise HTTPException(409, f"recheck failed: {why if not ok else 'unavailable'}")
            res = n.register({"domain": {"domainName": deal.domain},
                              "purchasePrice": float(entry.get("purchasePrice", 0) or 0)},
                             prov.idempotency_key(str(deal.id), deal.domain, "register"))
        transition(deal, "REGISTERED", f"order ok (live={_live()})")
        deal.result = {**deal.result, "order": str(res)[:500]}
    except HTTPException:
        raise
    except (prov.ProviderError, DealError) as e:
        try:
            transition(deal, "FAILED", str(e)[:200])
            db.commit()
        except DealError:
            pass
        raise HTTPException(502, str(e)[:300])
    db.commit()
    return {"ok": True, "deal_id": deal.id, "status": deal.status, "live": _live()}


@router.post("/{deal_id}/wire")
def wire(deal_id: int, worker: str = "cmail", db: Session = Depends(_db)):
    """Post-buy auto-wire: CF zone → nameservers → routing → worker → steve business.
    Name.com has no NS-update API: returns the manual NS step instead of failing."""
    from .models import Project

    deal = _deal(db, deal_id)
    if deal.status != "REGISTERED":
        raise HTTPException(400, f"wire only from REGISTERED (now {deal.status})")
    steps: dict[str, Any] = {}
    try:
        cf = _cf()
        zone = cf.find_zone(deal.domain) or cf.create_zone(deal.domain)
        zid = zone["id"]
        steps["zone"] = {"ok": True, "id": zid, "status": zone.get("status")}
        if deal.provider == "cloudflare":
            steps["nameservers"] = {"ok": True, "via": "registrar-is-cloudflare",
                                    "ns": zone.get("name_servers") or []}
        elif deal.provider == "porkbun":
            try:
                cf_ns = zone.get("name_servers") or []
                if cf_ns:
                    _porkbun(db).set_nameservers(deal.domain, cf_ns)
                    steps["nameservers"] = {"ok": True, "via": "porkbun-api", "ns": cf_ns}
                else:
                    steps["nameservers"] = {"ok": False, "note": "zone has no NS yet — retry verify later"}
            except prov.ProviderError as e:
                steps["nameservers"] = {"ok": False, "error": str(e)[:150]}
        else:
            zone_ns = zone.get("name_servers") or []
            steps["nameservers"] = {"ok": False, "manual": True,
                                    "note": f"name.com has no NS API — set NS to {zone_ns} in dashboard, then retry"}
        try:
            cf.enable_routing(zid)
            cf.catchall_to_worker(zid, worker)
            steps["routing"] = {"ok": True, "worker": worker}
        except prov.ProviderError as e:
            steps["routing"] = {"ok": False, "error": str(e)[:150],
                                "note": "retry once NS propagates (zone must be active)"}
        slug = deal.domain.split(".")[0].replace("-", "")
        proj = db.scalar(select(Project).where(Project.slug == slug))
        if proj is None:
            proj = Project(slug=slug, name=deal.domain, domain=deal.domain,
                           passport={"version": 1, "product": {"name": deal.domain},
                                     "resources": [{"key": "domain", "kind": "domain", "label": "Domain",
                                                    "desired": {"domain": deal.domain}}]})
            db.add(proj)
            db.flush()
        steps["business"] = {"ok": True, "slug": slug}
        deal.result = {**deal.result, "wire": steps}
        if steps.get("zone", {}).get("ok") and steps.get("business", {}).get("ok"):
            transition(deal, "WIRED", "zone+business ready; routing/NS may still propagate")
    except HTTPException:
        raise
    except (prov.ProviderError, DealError) as e:
        try:
            transition(deal, "FAILED", str(e)[:200])
        except DealError:
            pass
        db.commit()
        raise HTTPException(502, str(e)[:300])
    db.commit()
    return {"ok": True, "deal_id": deal.id, "status": deal.status, "steps": steps}


class Claim(BaseModel):
    domain: str
    provider: str = "auto"
    max_price: float = 25.0
    registrant_email: str = ""


@router.post("/claim")
def claim(body: Claim, db: Session = Depends(_db)):
    """One-click entry from the name checker: check + prepare a deal.
    Still gated downstream — approve + register need the human token."""
    return prepare(Prepare(domain=body.domain, provider=body.provider,
                           max_price=body.max_price, registrant_email=body.registrant_email), db)


@router.get("/renewals")
def renewals(warn_days: int = 30, db: Session = Depends(_db)):
    """Expiry monitor across Cloudflare registrations. Expiring soon → reconcile alert."""
    from datetime import datetime, timezone

    try:
        regs = _cf_reg(db).list_registrations()
    except HTTPException:
        raise
    except prov.ProviderError as e:
        raise HTTPException(502, str(e)[:200])
    now = datetime.now(timezone.utc)
    out = []
    for r in regs:
        exp = r.get("expires_at") or r.get("expiry")
        days = None
        try:
            days = (datetime.fromisoformat(str(exp).replace("Z", "+00:00")) - now).days
        except Exception:
            pass
        out.append({"domain": r.get("domain_name") or r.get("name"), "expires": exp,
                    "days_left": days, "state": r.get("status"),
                    "alert": days is not None and days <= warn_days})
    out.sort(key=lambda x: (x["days_left"] is None, x["days_left"]))
    return {"domains": out, "alerts": sum(1 for x in out if x["alert"])}


@router.post("/renewals/sync")
def renewals_sync(warn_days: int = 30, db: Session = Depends(_db)):
    """Turn expiring domains into HumanActions (dedupe by key). Call daily;
    the desk shows them with everything else — no separate dashboard."""
    from .models import HumanAction, Project

    data = renewals(warn_days, db)
    p = db.scalar(select(Project).order_by(Project.id))
    made = 0
    for d in data["domains"]:
        if not d["alert"]:
            continue
        key = f"renewal:{d['domain']}"
        if db.scalar(select(HumanAction).where(HumanAction.project_id == p.id,
                                               HumanAction.resource_key == key)) is None:
            db.add(HumanAction(project_id=p.id, resource_key=key,
                               title=f"🔁 {d['domain']} expires in {d['days_left']}d",
                               instructions=f"Renew {d['domain']} (expires {d['expires']}). "
                                            f"Budget-check against kernels, then renew at registrar.",
                               priority=60))
            made += 1
    db.commit()
    return {"ok": True, "alerts": data["alerts"], "actions_created": made}


@router.get("/deals")
def list_deals(status: str | None = None, db: Session = Depends(_db)):
    q = select(DomainDeal).order_by(DomainDeal.id.desc()).limit(50)
    if status:
        q = q.where(DomainDeal.status == status.upper())
    return {"deals": [{"id": d.id, "domain": d.domain, "provider": d.provider,
                       "status": d.status, "quoted_price": d.quoted_price} for d in db.scalars(q)]}


@router.get("/{deal_id}")
def receipt(deal_id: int, db: Session = Depends(_db)):
    deal = _deal(db, deal_id)
    return {"id": deal.id, "domain": deal.domain, "provider": deal.provider, "status": deal.status,
            "max_price": deal.max_price, "quoted_price": deal.quoted_price,
            "receipt": deal.receipt, "result": deal.result}
