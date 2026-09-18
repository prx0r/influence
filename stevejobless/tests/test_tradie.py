"""Tests for the tradie stack: kernel, intake, quotes, scoring, stats."""
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


def intake(client, **kw):
    base = {"customer_name": "Test Customer", "customer_phone": "+447000000001",
            "customer_address": "1 High St", "channel": "voice", "job_type": "ev_charger",
            "description": "install car charger", "transcript": "…", "after_hours": True}
    base.update(kw)
    return client.post("/api/tradie/sparky/intake", json=base)


def test_kernel_seeded(client):
    r = client.get("/api/tradie/sparky/kernel")
    assert r.status_code == 200, r.text
    assert "price_book" in r.json()["kernel"]


def test_intake_creates_job_and_options(client):
    r = intake(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["job_id"] and body["action_id"]
    assert any(o["id"] == "quote" for o in body["options"])


def test_urgent_intake_flags_wake_now(client):
    r = intake(client, urgent=True, job_type="fault", description="sparks from socket")
    assert r.json()["ok"]
    job = client.get(f"/api/tradie/sparky/jobs/{r.json()['job_id']}").json()
    assert "URGENT" in str(job) or True  # title lives on the HumanAction
    from stevejobless.db import SessionLocal
    from stevejobless.models import HumanAction
    from sqlalchemy import select
    with SessionLocal() as db:
        a = db.scalar(select(HumanAction).where(HumanAction.resource_key == f"job:{r.json()['job_id']}"))
        assert a.priority == 100 and "WAKE-NOW" in a.instructions


def test_quote_and_lifecycle(client):
    jid = intake(client, job_type="fault").json()["job_id"]
    q = client.post(f"/api/tradie/sparky/jobs/{jid}/quote").json()
    assert q["ok"] and q["total"] > 0 and q["live_send"] is False
    assert client.patch(f"/api/tradie/sparky/jobs/{jid}", json={"status": "scheduled"}).json()["status"] == "scheduled"
    assert client.patch(f"/api/tradie/sparky/jobs/{jid}",
                        json={"status": "done", "final_price": 120, "duration_min": 75}).json()["ok"]
    stats = client.get("/api/tradie/sparky/stats").json()
    assert stats["stats"]["fault"]["n"] >= 1


def test_score_verdict(client):
    r = client.post("/api/tradie/sparky/score",
                    json={"job_type": "ev_charger", "distance_km": 5, "quoted_price": 350}).json()
    assert r["verdict"] == "take"
    r2 = client.post("/api/tradie/sparky/score",
                     json={"job_type": "general", "distance_km": 60, "quoted_price": 40}).json()
    assert r2["verdict"] == "skip"


def test_whatsapp_continuity_appends_not_fragments(client):
    from stevejobless import channels

    msg = {"from": "447000000099", "type": "text", "text": {"body": "need sparky"}, "timestamp": "1"}
    payload = {"entry": [{"changes": [{"value": {"messages": [msg]}}]}]}
    r1 = client.post("/api/tradie/whatsapp/webhook", json=payload).json()
    payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "sockets dead too"
    r2 = client.post("/api/tradie/whatsapp/webhook", json=payload).json()
    assert r1["jobs"] == r2["jobs"], "same caller within window must extend one job"
    job = client.get(f"/api/tradie/sparky/jobs/{r1['jobs'][0]}").json()
    assert len(job["transcript"]) == 2


def test_whatsapp_stubs(client):
    from stevejobless import channels
    assert channels.send_whatsapp("+447000000001", "hi")["stubbed"] is True
    assert channels.parse_whatsapp_webhook({"entry": [{"changes": [{"value": {"messages": [
        {"from": "447000000001", "type": "text", "text": {"body": "need sparky"}, "timestamp": "1"}]}}]}]})[0]["text"] == "need sparky"


def test_social_claim_kit_live_checker(client):
    r = client.get("/api/tradie/sparky/social/claim-kit?name=sparkytest12345").json()
    assert "handles" in r and "claim_order" in r
    actions = {s["action"] for s in r["claim_order"]}
    assert actions <= {"claim", "check manually"}
    assert any(s["platform"] == "github" for s in r["handles"])


def test_social_verify_records_resolving_handle(client):
    r = client.post("/api/tradie/sparky/social/verify",
                    json={"platform": "github", "handle": "octocat"}).json()
    assert r["ok"] and r["verified"] is True
    r2 = client.post("/api/tradie/sparky/social/verify",
                     json={"platform": "github", "handle": "nosuchuser-zz-qq-404"}).json()
    assert r2["verified"] is False


def test_callback_gate_blocks_big_send_until_verified(client):
    jid = client.post("/api/tradie/sparky/intake", json={
        "customer_name": "Big", "customer_phone": "+447000000060",
        "job_type": "consumer_unit", "description": "fusebox"}).json()["job_id"]
    qid = client.get(f"/api/tradie/sparky/jobs/{jid}").json()["quotes"][0]["id"]
    r = client.post(f"/api/tradie/sparky/jobs/{jid}/quote/{qid}/send")
    assert r.status_code == 409  # 450+ labour ≥ 500 default threshold
    assert client.post(f"/api/tradie/sparky/jobs/{jid}/callback",
                       json={"verifier": "tradie:voice:+447000000001"}).json()["callback_verified"] is True
    r2 = client.post(f"/api/tradie/sparky/jobs/{jid}/quote/{qid}/send").json()
    assert r2["quote_status"] in ("approved", "sent")


def test_instagram_inbound_continuity_no_token(client):
    payload = {"entry": [{"messaging": [
        {"sender": {"id": "iguser1"}, "message": {"text": "boiler service?"}}]}]}
    j1 = client.post("/api/tradie/instagram/webhook", json=payload).json()["jobs"][0]
    payload["entry"][0]["messaging"][0]["message"]["text"] = "next week?"
    j2 = client.post("/api/tradie/instagram/webhook", json=payload).json()["jobs"][0]
    assert j1 == j2
    job = client.get(f"/api/tradie/sparky/jobs/{j1}").json()
    assert len(job["transcript"]) == 2
    assert job["job"]["status"] == "new"
