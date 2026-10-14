"""Tests for sleep_studio fish backend + studio grants. No network, no spend.

Grant flow is tested structurally (issue → redeem once → second redeem dead,
expired dead). Live Fish calls are infra-verified manually ($0 reads).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
_REPO = os.path.dirname(_HERE)
_CHAN = os.path.join(_REPO, "studio", "channels")
_DAMN = os.environ.get("DAMN_DIR", "/root/damn")
if not os.access(os.environ.get("SLEEPDRAW_DIR", "/root/sleepdraw"), os.W_OK) \
        and not os.access("/root", os.W_OK):
    import tempfile as _tf
    os.environ["SLEEPDRAW_DIR"] = _tf.mkdtemp(prefix="sleepdraw-")

import pytest  # noqa: E402

needs_damn = pytest.mark.skipif(not os.path.isdir(_DAMN),
                                reason="owner's damn tree not on this box")

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
    fx = _CHAN + "/_test_tmp.json"
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
        for p in (fx, _CHAN + "/_test_tmp.seed.json"):
            try: os.remove(p)
            except OSError: pass


def test_save_config_allowlist():
    import json as _j
    import channel_onboard as ob
    fx = _CHAN + "/_test_cfg.json"
    open(fx, "w").write(_j.dumps({"channel": "_test_cfg",
        "voice": {"chairs": {}}, "engine": "E2"}))
    try:
        assert ob.save_config("../x", {})["ok"] is False
        assert ob.save_config("_test_cfg", "nope")["ok"] is False
        assert ob.save_config("_test_cfg", {"engine": "HAX",
            "voice": {"x": 1}})["ok"] is False
        r = ob.save_config("_test_cfg", {
            "display_name": "Tmp!", "pitch": "p", "cadence": "daily",
            "style": {"accent": "#000", "manner": "m", "visual": "v",
                      "shelf": "S", "evil": "drop"},
            "thumbnail": {"type": "t", "rules": ["r1", "r2"]},
            "formats": [{"name": "F1", "length": "10min",
                         "reasoning": "why", "evil": 1}, {"length": "x"}]})
        assert r["ok"] is True, r
        back = _j.load(open(fx))
        assert back["display_name"] == "Tmp!"
        assert back["engine"] == "E2" and "evil" not in str(back)
        assert back["formats"] == [{"name": "F1", "length": "10min",
                                    "reasoning": "why"}]
    finally:
        try: os.remove(fx)
        except OSError: pass


def test_onboard_react_cycle():
    import channel_onboard as ob
    r = ob.react("folk-and-fable", "narrator", "v-test-1", "Test Voice",
                 liked=True, note="warm")
    assert r["ok"] is True and r["likes"] >= 1
    assert "v-test-1" in ob._liked_ids("folk-and-fable", "narrator")
    r2 = ob.react("folk-and-fable", "narrator", "v-test-2", dismissed=True)
    assert r2["ok"] is True
    assert "v-test-2" in ob._dismissed_ids("folk-and-fable")
    # cleanup test traces
    import json as _j
    p = _CHAN + "/folk-and-fable-taste.json"
    d = _j.load(open(p))
    d["likes"] = [l for l in d.get("likes", []) if not l.get("voice_id", "").startswith("v-test-")]
    d["dismissed"] = [x for x in d.get("dismissed", []) if not x.startswith("v-test-")]
    _j.dump(d, open(p, "w"))
    assert ob.react("xx", "n", "", liked=True)["ok"] is False


def test_design_instruction_pure_and_gated():
    import sleep_studio as st
    r = st.design_instruction("folk-and-fable", "narrator")
    assert r["ok"] is True and "Adrian" in r["instruction"]
    assert st.design_instruction("nope", "n")["ok"] is False
    assert st.design_instruction("folk-and-fable", "nobody")["ok"] is False
    import sys as _s
    _s.path.insert(0, os.path.join(_REPO, "pipeline"))
    from providers import fish_rest
    try:
        fish_rest.voice_design("warm voice", approved=False)
        assert False, "unapproved design must raise"
    except PermissionError:
        pass


def test_anchor_prompt_engine():
    import channel_onboard as ob
    assert ob.anchor_prompt("x", voice_ids=["nope"])["ok"] is False
    r = ob.anchor_prompt("sleep fairy", voice_ids=[
        "fe2619861dfc4bcab9da073029ca80a4"])
    assert r["ok"] is True and "Luna Lovegood" in r["sources"]
    assert "fairy" in r["instruction"] and len(r["instruction"]) <= 1800


@needs_damn
def test_pilots_list_and_parse_offline():
    import sleep_studio as st
    ps = st.list_pilots()
    assert len(ps) >= 16, len(ps)
    by = {p["file"]: p for p in ps}
    assert "01-yuki-doorway.drama.txt" in by
    p = st.parse_drama(_DAMN + "/projects/folk-and-fable/pilots/01-yuki-doorway.drama.txt")
    assert p["n_segments"] >= 3 and "narrator" in p["chairs"]
    try:
        st.parse_drama("/etc/passwd")
        assert False, "path escape must raise"
    except ValueError:
        pass


def test_r2_presign_offline():
    import os as _o
    _o.environ["R2_ENDPOINT"] = "https://x.r2.cloudflarestorage.com"
    _o.environ["R2_ACCESS_KEY"] = "testkey"
    _o.environ["R2_SECRET_KEY"] = "testsecret"
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from r2_presign import presign_get, audio_key
    u = presign_get("bkt", "audio/studio/x.mp3", expires=60)
    assert u.startswith("https://x.r2.cloudflarestorage.com/bkt/audio/studio/x.mp3?")
    assert "X-Amz-Signature=" in u and "X-Amz-Expires=60" in u
    assert audio_key("folk-and-fable", "a b.mp3") == "audio/folk-and-fable/a-b.mp3"
    for k in ("R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"):
        _o.environ.pop(k, None)


def test_ship_dryrun_offline():
    pytest.importorskip("boto3")
    import os as _o
    _o.environ["R2_ENDPOINT"] = "https://x.r2.cloudflarestorage.com"
    _o.environ["R2_ACCESS_KEY"] = "testkey"
    _o.environ["R2_SECRET_KEY"] = "testsecret"
    import sys as _s
    _s.path.insert(0, "/root/influence")
    from scripts import ship_audio
    r = ship_audio.ship(days=9999, dry_run=True)
    assert r["ok"] is True and r["dry_run"] is True
    assert all("fresh" in s for s in r["skipped"])
    for k in ("R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"):
        _o.environ.pop(k, None)
