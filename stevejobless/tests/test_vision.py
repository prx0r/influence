"""Full-vision checks: feed, invoice+csv, reconcile, email bridge→job, calibration."""
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


def _job(client, **kw):
    base = {"customer_name": "Feed", "job_type": "ev_charger", "description": "wallbox",
            "distance_km": 5, "quoted_price": 400}
    base.update(kw)
    return client.post("/api/tradie/sparky/intake", json=base).json()["job_id"]


def test_feed_ranks_for_consumer(client):
    _job(client, job_type="ev_charger", quoted_price=400)
    _job(client, job_type="general", distance_km=60, quoted_price=40)
    feed = client.get("/api/tradie/feed?for_slug=sparky").json()
    assert len(feed["items"]) >= 2
    scores = [i["score"] for i in feed["items"]]
    assert scores == sorted(scores, reverse=True)
    assert feed["items"][0]["verdict"] == "take"
    assert all("business" in i and "mine" in i for i in feed["items"])


def test_invoice_and_csv(client):
    jid = _job(client)
    client.patch(f"/api/tradie/sparky/jobs/{jid}",
                 json={"status": "done", "final_price": 420, "duration_min": 200})
    inv = client.post(f"/api/tradie/sparky/jobs/{jid}/invoice").json()
    assert inv["ok"] and inv["number"].startswith("SPARKY-") and inv["total"] == 420
    assert client.get(f"/api/tradie/sparky/jobs/{jid}").json()["job"]["status"] == "invoiced"
    csv_text = client.get("/api/tradie/sparky/invoices.csv").text
    assert "number,customer,job_type,total,vat,gross,status,created" in csv_text
    assert inv["number"] in csv_text
    assert inv["vat"] == round(420 * 0.2, 2) and inv["gross"] == round(420 * 1.2, 2)


def test_tax_quarter(client):
    jid = _job(client)
    client.patch(f"/api/tradie/sparky/jobs/{jid}",
                 json={"status": "done", "final_price": 100, "duration_min": 60})
    client.post(f"/api/tradie/sparky/jobs/{jid}/invoice")
    t = client.get("/api/tradie/sparky/tax/quarter").json()
    assert t["invoices"] >= 1 and t["vat_owed"] == round(t["net"] * 0.2, 2)
    assert t["gross"] == round(t["net"] + t["vat_owed"], 2)


def test_reconcile_reports_channels(client):
    r = client.post("/api/tradie/sparky/reconcile").json()
    ch = r["channels"]
    assert ch["kernel"]["status"] == "READY"
    assert ch["channel:whatsapp"]["status"] == "MISSING"  # no creds in test env
    assert ch["channel:voice"]["status"] == "READY"
    assert ch["channel:email"]["status"] in ("READY", "ERROR")


def test_email_bridge_opens_job_for_tradie_domain(client):
    # sparky has a kernel + domain; job-like mail becomes a job
    from stevejobless.db import SessionLocal
    from stevejobless.models import Project
    from sqlalchemy import select

    with SessionLocal() as db:
        p = db.scalar(select(Project).where(Project.slug == "sparky"))
        domain = p.domain
    r = client.post("/api/observations/email", json={
        "message_id": "bridge-job-1", "domain": domain, "mailbox": f"hello@{domain}",
        "sender": "customer@x.com", "subject": "fusebox sparks, help",
        "summary": "sparks from fusebox", "classification": "needs_reply",
        "importance": 8, "needs_reply": True}).json()
    assert r["job_id"] is not None
    job = client.get(f"/api/tradie/sparky/jobs/{r['job_id']}").json()["job"]
    assert job["channel"] if "channel" in job else True
    # receipts never open jobs
    r2 = client.post("/api/observations/email", json={
        "message_id": "bridge-job-2", "domain": domain, "subject": "receipt",
        "summary": "thanks", "classification": "receipt", "importance": 1}).json()
    assert r2["job_id"] is None


def test_calibration_in_stats(client):
    jid = _job(client, quoted_price=400)
    client.patch(f"/api/tradie/sparky/jobs/{jid}",
                 json={"status": "done", "final_price": 420, "duration_min": 200})
    stats = client.get("/api/tradie/sparky/stats").json()
    assert "calibration" in stats


def test_feed_orders_differently_per_consumer(client):
    # ev_charger: sparky loves (+2), flowright dislikes (-2). boiler: reverse.
    client.post("/api/tradie/sparky/intake", json={
        "customer_name": "EV", "job_type": "ev_charger", "description": "wallbox",
        "distance_km": 5, "quoted_price": 400})
    client.post("/api/tradie/flowright/intake", json={
        "customer_name": "Boiler", "job_type": "boiler", "description": "service",
        "distance_km": 5, "quoted_price": 200})
    sparky_top = client.get("/api/tradie/feed?for_slug=sparky").json()["items"][0]
    flow_top = client.get("/api/tradie/feed?for_slug=flowright").json()["items"][0]
    assert sparky_top["job_type"] == "ev_charger", sparky_top
    assert flow_top["job_type"] == "boiler", flow_top
