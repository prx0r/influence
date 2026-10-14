"""Tests for sleep_studio fish backend + studio grants. No network, no spend.

Grant flow is tested structurally (issue → redeem once → second redeem dead,
expired dead). Live Fish calls are infra-verified manually ($0 reads).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import studio_grants as sg


def test_grant_single_use():
    payload = {"tool": "text_to_speech", "text": "hi", "voice_id": "v",
               "credits": 2}
    g = sg.issue("audio.speak", payload)
    assert g["payload_hash"].startswith("sha256:")
    r1 = sg.redeem(g["grant_id"])
    assert r1 is not None and r1["action"] == "audio.speak"
    assert r1["payload_hash"] == g["payload_hash"]
    assert sg.redeem(g["grant_id"]) is None  # spent
    assert sg.redeem("sg_nope") is None


def test_grant_expired_dead():
    import time
    g = sg.issue("audio.speak", {"x": 1})
    d = sg._load()
    d[g["grant_id"]]["expires_at"] = int(time.time()) - 1
    sg._save(d)
    assert sg.redeem(g["grant_id"]) is None


def test_fish_quote_pure():
    import sleep_studio as st
    q = st.fish_quote("hello")
    assert q["ok"] is True
    assert q["quote"]["bytes"] == 5 and q["quote"]["credits"] == 5


def test_fish_narrate_dryrun_no_grant():
    import sleep_studio as st
    r = st.fish_narrate("Hello world", "voice-123")
    assert r["ok"] is True and r["dry_run"] is True
    assert r["payload_hash"].startswith("sha256:")


def test_grant_payload_matches_audio_flow():
    """The hash the approve button binds must equal audio_flow's own hash."""
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "pipeline"))
    from audio_flow import speak
    import sleep_studio as st
    dry = st.fish_narrate("abc", "v1")
    live_shape = speak("abc", "v1", dry_run=True)
    assert dry["payload_hash"] == live_shape["payload_hash"]


def test_onboard_queries_pure():
    import channel_onboard as ob
    ch = {"display_name": "Test", "pitch": "calm sleep tales",
          "voice": {"chairs": {"narrator": {"direction": "warm unhurried male"}}}}
    qs = ob.vibe_queries(ch, "narrator")
    assert 1 <= len(qs) <= 3 and all(qs)


def test_onboard_lock_cycle():
    import json as _j
    import channel_onboard as ob
    fx = "/root/influence/studio/channels/_test_tmp.json"
    rec = {"channel": "_test_tmp", "display_name": "Tmp",
           "voice": {"chairs": {"narrator": {"direction": "calm"}}}}
    open(fx, "w").write(_j.dumps(rec))
    try:
        assert ob.lock("_test_tmp", "narrator", "", "")["ok"] is False
        assert ob.lock("_test_tmp", "nope", "v", "r")["ok"] is False
        r = ob.lock("_test_tmp", "narrator", "v123", "sounds right")
        assert r["ok"] is True
        back = _j.load(open(fx))
        assert back["voice"]["chairs"]["narrator"]["fish_id"] == "v123"
        assert back["voice"]["chairs"]["narrator"]["lock_reason"] == "sounds right"
    finally:
        for p in (fx, "/root/influence/studio/channels/_test_tmp.seed.json"):
            try: os.remove(p)
            except OSError: pass
