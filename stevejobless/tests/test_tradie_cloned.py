"""Cloned-pattern checks: availability, lifecycle, autonomy, privacy, parts."""
import os
import tempfile
from datetime import datetime, timedelta, timezone

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


def test_slots_are_future_working_hours(client):
    slots = client.get("/api/tradie/sparky/slots?job_type=ev_charger").json()["slots"]
    assert 1 <= len(slots) <= 5
    now = datetime.now(timezone.utc)
    for s in slots:
        assert datetime.fromisoformat(s["start"]) > now
    assert slots[0]["part"] == "morning"  # sparky prefers mornings


def test_slots_skip_busy(client):
    jid = client.post("/api/tradie/sparky/intake", json={
        "customer_name": "Busy", "job_type": "fault", "description": "x"}).json()["job_id"]
    slot = client.get("/api/tradie/sparky/slots").json()["slots"][0]["start"]
    r = client.post(f"/api/tradie/sparky/jobs/{jid}/confirm", json={"scheduled_at": slot}).json()
    assert r["intake_state"] == "confirmed" and r["scheduled_at"]
    again = client.get("/api/tradie/sparky/slots").json()["slots"]
    assert slot not in [s["start"] for s in again]


def test_confirm_lifecycle(client):
    jid = client.post("/api/tradie/sparky/intake", json={
        "customer_name": "Life", "job_type": "fault", "description": "x"}).json()["job_id"]
    job = client.get(f"/api/tradie/sparky/jobs/{jid}").json()["job"]
    assert job["status"] in ("new", "quoted")
    slot = client.get("/api/tradie/sparky/slots").json()["slots"][0]["start"]
    client.post(f"/api/tradie/sparky/jobs/{jid}/confirm", json={"scheduled_at": slot})
    assert client.get(f"/api/tradie/sparky/jobs/{jid}").json()["job"]["status"] == "scheduled"


def test_semi_auto_drafts_quote_on_intake(client):
    r = client.post("/api/tradie/sparky/intake", json={
        "customer_name": "Auto", "job_type": "ev_charger", "description": "wallbox",
        "distance_km": 5}).json()
    assert r["autonomy"] == "semi_auto"
    job = client.get(f"/api/tradie/sparky/jobs/{r['job_id']}").json()
    assert len(job["quotes"]) == 1 and job["job"]["score"] is not None


def test_observe_logs_only(client):
    kernel = client.get("/api/tradie/sparky/kernel").json()["kernel"]
    client.put("/api/tradie/sparky/kernel", json={**kernel, "autonomy": "observe"})
    try:
        r = client.post("/api/tradie/sparky/intake", json={
            "customer_name": "Quiet", "job_type": "fault", "description": "x"}).json()
        assert r["autonomy"] == "observe"
        job = client.get(f"/api/tradie/sparky/jobs/{r['job_id']}").json()
        assert job["quotes"] == [] and job["job"]["status"] == "new"
    finally:
        client.put("/api/tradie/sparky/kernel", json=kernel)


def test_sweep_needs_confirm_and_purges(client):
    from stevejobless.db import SessionLocal
    from stevejobless.tradie import Job, JobMessage
    from stevejobless.models import Project
    from sqlalchemy import select

    with SessionLocal() as db:
        p = db.scalar(select(Project).where(Project.slug == "sparky"))
        j = Job(project_id=p.id, customer_name="Old", status="done")
        db.add(j)
        db.flush()
        m = JobMessage(job_id=j.id, role="customer", channel="voice", content="old transcript")
        m.created_at = datetime.now(timezone.utc) - timedelta(days=200)
        db.add(m)
        db.commit()
        jid = j.id
    assert client.post("/api/tradie/sparky/sweep").status_code == 400
    r = client.post("/api/tradie/sparky/sweep?confirm=true").json()
    assert r["deleted"] >= 1
    with SessionLocal() as db:
        assert db.scalar(select(Job).where(Job.id == jid)) is not None  # metadata kept


def test_privacy_redact():
    from stevejobless.privacy import redact

    out = redact("call me on +44 7000 123456 or bob@x.com, SW1A 1AA")
    assert "+44" not in out and "bob@x.com" not in out and "SW1A" not in out
    assert "[phone]" in out and "[email]" in out


def test_parts_lookup_falls_back():
    from stevejobless import parts

    r = parts.lookup("32A RCBO")
    assert r["price"] == 45.0 and r["live"] is False
    assert parts.lookup("unobtainium")["price"] is None


def test_agent_profile():
    from stevejobless.main import app

    with TestClient(app) as c:
        p = c.get("/.well-known/agent-profile.json").json()
        assert "jobs.intake" in p["capabilities"]


def test_instagram_inbound_continuity(client):
    payload = {"entry": [{"messaging": [
        {"sender": {"id": "111"}, "message": {"text": "boiler service?"}}]}]}
    j1 = client.post("/api/tradie/instagram/webhook", json=payload).json()["jobs"][0]
    payload["entry"][0]["messaging"][0]["message"]["text"] = "next week?"
    j2 = client.post("/api/tradie/instagram/webhook", json=payload).json()["jobs"][0]
    assert j1 == j2
    assert client.get("/api/tradie/instagram/webhook?hub_verify_token=x").status_code == 403


def test_instagram_send_stubs_without_token():
    from stevejobless import channels

    assert channels.send_instagram("111", "hi")["stubbed"] is True
    assert channels.parse_instagram_webhook(
        {"entry": [{"messaging": [{"sender": {"id": "9"}, "message": {"text": "yo"}}]}]})[0]["from"] == "ig:9"
    assert channels.parse_instagram_webhook(
        {"entry": [{"messaging": [{"sender": {"id": "9"}, "message": {"is_echo": True, "text": "echo"}}]}]}) == []
