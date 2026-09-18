"""Reasoning checks for quote builder, scorer, stats — no I/O, no fixtures."""
from stevejobless.tradie import build_quote, job_stats, score_job

KERNEL = {
    "preferences": {"preferred_slots": ["morning"], "max_distance_km": 25,
                    "min_job_value": 90, "takes_emergency": False,
                    "job_affinity": {"ev_charger": 2, "fault": 0},
                    "max_typical_min": 300},
    "after_hours_multiplier": 1.5, "callout_per_km": 1.2, "default_range": [80, 150],
    "price_book": {"ev_charger": {"labour": 350, "typical_parts": ["32A RCBO"]}},
}


def test_quote_known_job_maths():
    q = build_quote(KERNEL, {"customer_name": "A", "job_type": "ev_charger",
                             "distance_km": 10, "after_hours": True})
    assert q["total"] == round(350 * 1.5 + 10 * 1.2, 2)  # 537.0
    assert not q["needs_review"]
    assert "£537" in q["message"]


def test_quote_unknown_job_never_invents():
    q = build_quote(KERNEL, {"customer_name": "B", "job_type": "rewire_castle"})
    assert q["needs_review"] is True
    assert "site visit" in q["message"]  # diagnosis, not a fake fixed price


def test_quote_no_distance_no_callout_line():
    q = build_quote(KERNEL, {"job_type": "ev_charger"})
    assert all("Callout" not in i["label"] for i in q["line_items"])
    assert q["total"] == 350.0


def test_score_orders_same_feed_per_tradie():
    good = score_job(KERNEL, {"job_type": "ev_charger", "distance_km": 5, "quoted_price": 350})
    bad = score_job(KERNEL, {"job_type": "general", "distance_km": 60, "quoted_price": 40})
    assert good["verdict"] == "take" and bad["verdict"] == "skip"
    assert good["score"] > bad["score"]


def test_score_penalises_emergency_avoider():
    s = score_job(KERNEL, {"job_type": "fault", "urgent": True, "quoted_price": 200})
    assert any("emergencies" in r for r in s["reasons"])


def test_score_penalises_over_max_distance():
    s = score_job(KERNEL, {"job_type": "ev_charger", "distance_km": 40, "quoted_price": 500})
    assert any("max" in r for r in s["reasons"]) and s["score"] < 65


def test_score_uses_duration_stats():
    stats = {"ev_charger": {"avg_min": 400}}
    s = score_job(KERNEL, {"job_type": "ev_charger", "quoted_price": 350}, stats)
    assert any("long job" in r for r in s["reasons"])


def test_stats_ignores_open_jobs_and_handles_empty():
    assert job_stats([]) == {}
    rows = [{"job_type": "fault", "status": "new", "duration_min": None,
             "final_price": None, "quoted_price": 142},
            {"job_type": "fault", "status": "done", "duration_min": 80,
             "final_price": 135, "quoted_price": 142}]
    st = job_stats(rows)
    assert st["fault"] == {"n": 1, "avg_min": 80.0, "avg_revenue": 135.0}


def test_calibration_bands_provisional():
    from stevejobless.tradie import calibration

    jobs = [
        {"score": 80, "status": "done", "final_price": 400, "quoted_price": 380},
        {"score": 70, "status": "lost", "final_price": None, "quoted_price": 400},
        {"score": 50, "status": "done", "final_price": 200, "quoted_price": 200},
        {"score": 20, "status": "lost", "final_price": None, "quoted_price": 100},
        {"score": None, "status": "done", "final_price": 1, "quoted_price": 1},
    ]
    cal = calibration(jobs)
    assert cal["take(65+)"]["n"] == 2 and cal["take(65+)"]["win_rate"] == 0.5
    assert cal["take(65+)"]["avg_margin"] == round(400 / 380, 2)
    assert cal["maybe(40-65)"]["win_rate"] == 1.0
    # provisional: weights v1 stand until 20+ real closed jobs, then retune bands
