"""Backend tests: telephony parsing, LiveKit config, gcal URL, setup routes."""
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


def test_parse_call_completed():
    from stevejobless.telephony import parse_call_event

    ev = parse_call_event({"data": {"event_type": "call.hangup", "payload": {
        "call_control_id": "abc", "from": "+447000", "to": "+441000",
        "call_duration_secs": 95, "hangup_cause": "normal"}}})
    assert ev["kind"] == "completed" and ev["from"] == "+447000" and ev["duration_sec"] == 95


def test_parse_ignores_noise():
    from stevejobless.telephony import parse_call_event

    assert parse_call_event({"data": {"event_type": "call.started", "payload": {}}}) is None
    assert parse_call_event({}) is None


def test_parse_sms():
    from stevejobless.telephony import parse_sms_event

    m = parse_sms_event({"data": {"event_type": "message.received", "payload": {
        "from": {"phone_number": "+447"}, "to": {"phone_number": "+441"}, "text": "yes 9am"}}})
    assert m == {"from": "+447", "to": "+441", "text": "yes 9am"}
    assert parse_sms_event({"data": {"event_type": "message.sent", "payload": {}}}) is None


def test_sip_config_validates():
    from stevejobless import livekit_cfg

    cfg = livekit_cfg.sip_trunk_config("+441000", "sip.livekit.cloud")
    problems = livekit_cfg.validate_sip_config(cfg)
    assert any("placeholder" in p for p in problems)  # password unset
    assert any("allowed SIP" in p for p in problems)
    cfg["trunk"]["auth"]["password"] = "s3cret"
    cfg["trunk"]["allowed_addresses"] = ["1.2.3.0/24"]
    cfg["egress"]["webhook"] = "https://brain/x?slug=sparky"
    assert livekit_cfg.validate_sip_config(cfg) == []


def test_gcal_auth_url():
    from stevejobless import gcal

    u = gcal.auth_url("cid", "https://x/cb", "sparky")
    assert "access_type=offline" in u and "calendar" in u and "state=sparky" in u


def test_telnyx_needs_key_first(client):
    r = client.get("/api/backend/sparky/telnyx/numbers")
    assert r.status_code == 409


def test_voice_webhook_opens_job(client):
    r = client.post("/api/backend/telnyx/voice-webhook?slug=sparky", json={
        "data": {"event_type": "call.hangup", "payload": {
            "call_control_id": "t1", "from": "+447000000055", "to": "+441000",
            "call_duration_secs": 120}}}).json()
    assert r["ok"] and r["job_id"]
    job = client.get(f"/api/tradie/sparky/jobs/{r['job_id']}").json()["job"]
    assert job["status"] == "new"


def test_voice_webhook_non_completed_no_job(client):
    r = client.post("/api/backend/telnyx/voice-webhook?slug=sparky", json={
        "data": {"event_type": "call.answered", "payload": {}}}).json()
    assert r["ok"] and "job_id" not in r


def test_sms_webhook_continuity(client):
    p1 = {"data": {"event_type": "message.received", "payload": {
        "from": {"phone_number": "+447000000056"}, "to": {"phone_number": "+441"},
        "text": "is tuesday free?"}}}
    j1 = client.post("/api/backend/telnyx/sms-webhook?slug=sparky", json=p1).json()["job_id"]
    p1["data"]["payload"]["text"] = "morning please"
    j2 = client.post("/api/backend/telnyx/sms-webhook?slug=sparky", json=p1).json()["job_id"]
    assert j1 == j2


def test_sms_confirm_stubs_honestly(client):
    jid = client.post("/api/tradie/sparky/intake", json={
        "customer_name": "SMS", "customer_phone": "+447000000057",
        "job_type": "fault", "description": "x"}).json()["job_id"]
    r = client.post(f"/api/tradie/sparky/jobs/{jid}/sms", json={"text": "on my way"}).json()
    assert r["ok"] and r["result"]["stubbed"] is True


def test_reconcile_backend_keys_present(client):
    ch = client.post("/api/tradie/sparky/reconcile").json()["channels"]
    assert ch["backend:telnyx"]["status"] == "MISSING"
    assert ch["backend:livekit"]["status"] == "MISSING"
    assert ch["backend:gcal"]["status"] == "MISSING"


def test_sip_config_needs_number(client):
    assert client.get("/api/backend/sparky/livekit/sip-config").status_code == 409
