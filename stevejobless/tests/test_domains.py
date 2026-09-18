"""Domain deal tests — state machine, guards, receipts. No network, no spend."""
import os
import tempfile

_fd, _db = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["STEVE_DB_URL"] = f"sqlite:///{_db}"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from stevejobless.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _init_db():
    from stevejobless.db import init_db

    init_db()


def test_transitions_guarded():
    from stevejobless.db import SessionLocal
    from stevejobless.domain_deals import DealError, DomainDeal, transition

    with SessionLocal() as db:
        d = DomainDeal(domain="x.test", provider="porkbun")
        db.add(d)
        db.flush()
        try:
            transition(d, "REGISTERED")
            assert False, "must not skip states"
        except DealError:
            pass
        transition(d, "PREPARED")
        assert d.status == "PREPARED" and len(d.receipt) == 1
        db.rollback()


def test_approval_token_single_use_shape():
    from stevejobless.db import SessionLocal
    from stevejobless.domain_deals import DealError, DomainDeal, check_approval, mint_approval, transition

    with SessionLocal() as db:
        d = DomainDeal(domain="y.test", provider="porkbun")
        db.add(d)
        db.flush()
        transition(d, "PREPARED")
        raw = mint_approval(d)
        assert len(raw) == 32 and d.approval_hash != raw
        try:
            check_approval(d, "wrong")
            assert False
        except DealError:
            pass
        db.rollback()


def test_price_guards_fail_closed():
    from stevejobless.domain_deals import price_ok

    assert price_ok(None, 10, 25)[0] is False
    assert price_ok(30, 30, 25)[0] is False
    assert price_ok(12, 10, 25)[0] is False  # 20% drift
    assert price_ok(10.5, 10, 25) == (True, "ok")


def test_providers_status_no_creds(client):
    p = client.get("/api/domains/providers").json()
    assert p["live"] is False
    assert p["porkbun"]["sandbox"] is True


def test_check_without_creds_409(client):
    r = client.get("/api/domains/check?domain=example12345.com&provider=porkbun")
    assert r.status_code == 409


def test_prepare_rejects_unavailable_without_network(client, monkeypatch):
    import stevejobless.domain_routes as dr

    monkeypatch.setattr(dr, "CHECKER", "http://127.0.0.1:9")
    r = client.post("/api/domains/prepare", json={
        "domain": "example12345.com", "provider": "porkbun", "max_price": 25,
        "registrant_email": "t@t.com"})
    # creds missing → 409 before any network spend path
    assert r.status_code == 409


def test_auto_picks_cheapest_configured(client, monkeypatch):
    import stevejobless.domain_routes as dr

    async_calls = {"n": 0}

    class FakePorkbun:
        def check(self, domain):
            return {"domain": domain, "available": True, "price": "9.99", "premium": False}

    class FakeNameCom:
        def check_fail_closed(self, domain):
            return {"domainName": domain, "purchasable": True, "purchaseType": "registration",
                    "purchasePrice": 19.99, "premium": False}

    monkeypatch.setattr(dr, "_porkbun", lambda db: FakePorkbun())
    monkeypatch.setattr(dr, "_namecom", lambda db: FakeNameCom())
    r = client.post("/api/domains/prepare", json={
        "domain": "cheaptest12345.com", "provider": "auto", "max_price": 25,
        "registrant_email": "t@t.com"}).json()
    assert r["provider"] == "porkbun" and r["price"] == 9.99
    assert client.get(f"/api/domains/{r['deal_id']}").json()["result"]["all_quotes"] == {
        "porkbun": 9.99, "namecom": 19.99}


def test_register_needs_approval(client):
    from stevejobless.db import SessionLocal
    from stevejobless.domain_deals import DomainDeal

    with SessionLocal() as db:
        d = DomainDeal(domain="z.test", provider="porkbun", status="PREPARED")
        db.add(d)
        db.commit()
        did = d.id
    r = client.post(f"/api/domains/{did}/register", json={"approval_token": "nope"})
    assert r.status_code == 403
    r2 = client.get(f"/api/domains/{did}").json()
    assert r2["status"] == "PREPARED" and isinstance(r2["receipt"], list)


def test_cloudflare_excluded_tld_never_buys():
    from stevejobless.domains import CloudflareRegistrar

    cf = CloudflareRegistrar("x", "y")
    r = cf.check("something.lol")
    assert r["available"] is False and "via_api" in r["reason"]


def test_cloudflare_register_gated_without_live():
    from stevejobless.domains import CloudflareRegistrar, ProviderError

    cf = CloudflareRegistrar("x", "y")
    try:
        cf.register("x.dev", allow_live=False)
        assert False
    except ProviderError as e:
        assert "no sandbox" in str(e)


def test_claim_prepares_in_one_call(client, monkeypatch):
    import stevejobless.domain_routes as dr

    class FakeNameCom:
        def check_fail_closed(self, domain):
            return {"domainName": domain, "purchasable": True, "purchaseType": "registration",
                    "purchasePrice": 12.0, "premium": False}

    monkeypatch.setattr(dr, "_namecom", lambda db: FakeNameCom())
    monkeypatch.setattr(dr, "_cf_reg", lambda db: (_ for _ in ()).throw(
        __import__("fastapi").HTTPException(409, "no token")))
    r = client.post("/api/domains/claim", json={
        "domain": "claimtest12345.com", "max_price": 25,
        "registrant_email": "t@t.com"}).json()
    assert r["status"] == "PREPARED" and r["provider"] == "namecom"
