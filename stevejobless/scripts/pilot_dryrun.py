"""A6 pilot dry-run: full SKILL.md onboarding against an isolated DB.
Proves the onboarding path without touching live data."""
import os
import tempfile

_fd, _db = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["STEVE_DB_URL"] = f"sqlite:///{_db}"

from fastapi.testclient import TestClient

from stevejobless.main import app

KERNEL = {
    "preferences": {"preferred_slots": ["morning"], "max_distance_km": 20,
                    "min_job_value": 50, "takes_emergency": True,
                    "job_affinity": {"fault": 1}, "max_typical_min": 240},
    "after_hours_multiplier": 1.5, "callout_per_km": 1.0, "default_range": [80, 150],
    "autonomy": "semi_auto", "retention_days": 90,
    "price_book": {"fault": {"labour": 90, "typical_parts": []}},
    "hours": {"monday-friday": "08:00-18:00"},
}

with TestClient(app) as c:
    # skill step: kernel load (project seeded? create via API if missing)
    projs = c.get("/api/projects").json()
    assert any(p["slug"] == "sparky" for p in projs), "seed missing"
    r = c.put("/api/tradie/sparky/kernel", json=KERNEL)
    assert r.json()["ok"], r.text
    # intake → quote → confirm → done → invoice → stats
    jid = c.post("/api/tradie/sparky/intake", json={
        "customer_name": "Dry Run", "customer_phone": "+447000000000",
        "job_type": "fault", "description": "dry run", "distance_km": 5}).json()["job_id"]
    q = c.post(f"/api/tradie/sparky/jobs/{jid}/quote").json()
    assert q["total"] == 90 + 5 * 1.0, q
    slot = c.get("/api/tradie/sparky/slots").json()["slots"][0]["start"]
    assert c.post(f"/api/tradie/sparky/jobs/{jid}/confirm", json={"scheduled_at": slot}).json()["ok"]
    assert c.patch(f"/api/tradie/sparky/jobs/{jid}",
                   json={"status": "done", "final_price": 95, "duration_min": 60}).json()["ok"]
    inv = c.post(f"/api/tradie/sparky/jobs/{jid}/invoice").json()
    assert inv["total"] == 95 and inv["vat"] == 19.0, inv
    s = c.get("/api/tradie/sparky/stats").json()
    assert "calibration" in s
    print("PILOT DRY-RUN OK: kernel→intake→quote(95.0)→slots→confirm→done→invoice→stats")
