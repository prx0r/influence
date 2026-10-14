"""Tests for native Story Studio flow. No network, no spend.

Only offline paths are tested: validation refuses + live-without-grant
fail-closed. Free server reads (import/status/generate-dryrun) are
infra-verified manually, never in the suite.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from audio_flow import (studio_generate, studio_export, studio_status,
                        studio_import)


def test_studio_validation_pure():
    assert studio_status("")["ok"] is False
    assert studio_import("")["ok"] is False
    assert studio_generate("", dry_run=False)["ok"] is False
    assert studio_export("")["ok"] is False


def test_studio_generate_live_fails_closed():
    r = studio_generate("proj-1", dry_run=False)
    assert r["ok"] is False and "FAIL CLOSED" in r["reason"]
    r2 = studio_generate("proj-1", dry_run=False, ctx={})
    assert r2["ok"] is False


def test_studio_export_live_fails_closed():
    r = studio_export("proj-1", confirmed_credits=500)
    assert r["ok"] is False and "FAIL CLOSED" in r["reason"]
    r2 = studio_export("proj-1", confirmed_credits=500, ctx={"grant": {}})
    assert r2["ok"] is False


def test_episode_import_gate_pure():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "dash"))
    import sleep_studio as st
    # empty refused before any network
    assert st.studio_import_episode("t", "")["ok"] is False
    # gate threshold respected (strict bar refuses middling copy)
    mid = "Buy now!!! Click https://x.com/a $5 $5 $5 visit today!!!"
    assert st.studio_import_episode("t", mid, min_score=99)["ok"] is False
    # healthy prose passes the gate structurally (network would follow)
    import unittest.mock as _mock
    good = ("Settle in. Let the day dissolve behind you. " * 20)
    with _mock.patch.object(st, "_audio_flow") as _af:
        _af.return_value.studio_import.return_value = {"ok": True, "data": {}}
        r = st.studio_import_episode("t", good)
        assert r["ok"] is True and r["score"] >= 70


def test_mcp_registers_studio_tools():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "dash"))
    import mcp as dash_mcp
    names = {t["name"] for t in dash_mcp.TOOLS}
    for n in ("audio.studio.import", "audio.studio.status",
              "audio.studio.generate", "audio.studio.export"):
        assert n in names, n


def test_pi_gets_studio_status_only():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "dash"))
    import agent_chat
    assert "audio.studio.status" in agent_chat.READONLY_TOOLS
    assert "audio.studio.import" not in agent_chat.READONLY_TOOLS
    assert "audio.studio.generate" not in agent_chat.READONLY_TOOLS
    assert "audio.studio.export" not in agent_chat.READONLY_TOOLS


def test_free_rest_refuses_paid_and_bad_input():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "providers"))
    from providers import fish_rest
    assert fish_rest.tts("", "v")["ok"] is False
    assert fish_rest.tts("x" * 16000, "v")["ok"] is False
    try:
        fish_rest.tts("hi", "v", model="s2.1-pro")
        assert False, "paid model must raise"
    except PermissionError:
        pass
    assert fish_rest.MODEL_FREE == "s2.1-pro-free"


def test_speak_free_validation_offline():
    from audio_flow import speak_free
    assert speak_free("", "v")["ok"] is False


def test_channel_character_binding():
    import channel_character as cc
    ch = cc.load_channel('folk-and-fable')
    d = cc.compile_direction(ch['voice']['chairs']['narrator'], ch)
    assert d.startswith('[') and 'never' not in d  # narrator has no nevers
    a = cc.compile_direction(ch['voice']['chairs']['yuki'] if 'fish_id' in ch['voice']['chairs'].get('yuki', {}) else {'direction': 'soft', 'never': ['rush']}, ch)
    assert 'never rush' in a
    try:
        cc.roster_for_duel(ch, ['narrator', 'nobody'])
        assert False, "unlocked chair must raise"
    except ValueError:
        pass
    s = cc.to_seed(ch)
    assert s['character_id'] == 'channel-folk-and-fable'
    assert s['seed']['modulator_range'] and s['instances'] == []


def test_audio_request_queues_without_spending(tmp_path):
    from audio_flow import audio_request
    db = str(tmp_path / "t.db")
    assert audio_request("nope", {}, db_path=db)["ok"] is False
    assert audio_request("speak", {"text": "", "voice_id": "v"},
                         db_path=db)["ok"] is False
    r = audio_request("speak", {"text": "Settle in.", "voice_id": "v-test"},
                      brand="sleepdraw", db_path=db)
    assert r["ok"] is True and r["state"] == "REVIEW_READY"
    assert r["payload_hash"].startswith("sha256:")
    assert r["quote"]["credits"] == 10
    from effects import get_task
    t = get_task(r["task_id"], db_path=db)
    assert t["state"] == "REVIEW_READY" and t["kind"] == "audio.speak"


def test_spend_killswitch_blocks_live_paths():
    from audio_flow import speak, generate_media, studio_generate
    fake_grant = {"grant": {"action": "x", "payload_hash": "y",
                            "expires_at": 9999999999}}
    for r in (speak("hi", "v", dry_run=False, ctx=fake_grant),
              generate_media("image", "w", "m", "p", 1, dry_run=False,
                             ctx=fake_grant),
              studio_generate("proj", dry_run=False, ctx=fake_grant)):
        assert r["ok"] is False and "DISABLED" in r["reason"]


def test_cast_extract_yuki():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from cast_extract import cast_book
    r = cast_book("/root/easy/folk-and-fable/yuki-onna/source.txt",
                  min_freq=2)
    names = {c["name"] for c in r["characters"]}
    assert {"Minokichi", "Yuki", "Mosaku"} <= names
    yuki = next(c for c in r["characters"] if c["name"] == "Yuki")
    assert yuki["gender"] == "female" and "female" in yuki["voice_query"]
    mos = next(c for c in r["characters"] if c["name"] == "Mosaku")
    assert mos["gender"] == "male"
    assert all("dialogue_how" in c and "voice_query" in c
               for c in r["characters"])


def test_cast_drops_common_nouns():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from cast_extract import dramatis
    text = ("The old table stood in the hall, and Kai loved the table. "
            "Birds sat on the table while Kai watched the old table. "
            "Gerda loves Kai. Kai runs to Gerda. Gerda sings "
            "with Kai. Kai shouts for Gerda.")
    names = {c["name"] for c in dramatis(text, min_freq=2)}
    assert "Table" not in names and "Kai" in names and "Gerda" in names


def test_ensemble_cast_offline():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from ensemble_cast import (pitch_band, brief_character,
                               design_instruction_for, compose_cast,
                               contrast_notes)
    assert pitch_band("giant", None, None) == (70, 110)
    assert pitch_band(None, None, "female") == (160, 240)
    tree = {"name": "Oak", "role": None, "age": "old", "gender": None,
            "dialogue_lines": 4}
    mouse = {"name": "Nib", "role": None, "age": "young", "gender": None,
             "dialogue_lines": 9}
    assert "85-130Hz" in brief_character(tree) and "sleep baseline" in brief_character(tree)
    di = design_instruction_for(mouse, "sleep tales")
    assert "140-200Hz" in di and "sleep" in di.lower()
    cast = compose_cast([mouse, tree], context="sleep tales")
    assert cast[0]["name"] == "Nib" and len(cast) == 2
    assert all("design_instruction" in c and "voice_query" in c for c in cast)
    dup = compose_cast([dict(mouse, voice_query="young narration"),
                        dict(tree, voice_query="young narration")])
    assert any("contrast" in n or "share query" in n for n in contrast_notes(dup))


def test_fal_gates():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from providers import fal as F
    assert F._spend_allowed()["ok"] is False
    assert F.run("x", ctx=None)["ok"] is False
    p = F.build_request("moon", "flux_schnell")
    assert p["est_usd"] == 0.01 and "queue.fal.run" in p["endpoint"]


def test_yt_compliance_gates():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from yt_compliance import check_metadata, check_thumbnail, check_package
    good = {"title": "Yuki-Onna — Sleep Reading | 1 Hour",
            "description": "Ritual line.", "tags": ["sleep", "folklore"],
            "categoryId": "27", "madeForKids": False,
            "privacyStatus": "unlisted"}
    assert check_metadata(good)["ok"] is True
    bad = dict(good, title="x" * 101, madeForKids=None,
               privacyStatus="public")
    r = check_metadata(bad)
    assert r["ok"] is False and len(r["failures"]) == 3
    assert check_thumbnail("/nope.jpg")["ok"] is False
    assert check_package("/nope.mp4", "/nope.jpg", good)["ok"] is False
    assert check_package("/nope.mp4", "/nope.jpg", good)["quota_note"]


def test_taste_profile_compiles_and_calibrates():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from taste_profile import compile_profile, weight_of, load_profile
    p = compile_profile()
    assert p["n_features"] > 10 and p["version"] >= 2
    assert "lanes" in p and "sleepy" in p["lanes"]
    assert weight_of("narration", 0.5) > 0.5  # learned positive
    assert weight_of("zzz-no-such-tag-zzz", 0.5) == 0.5  # default
    assert isinstance(load_profile().get("rules"), list)


def test_calibration_studio_fits_functions():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    import shutil as _sh
    _bak_p, _bak_j = "/tmp/tp-pairs.bak", "/tmp/tp-profile.bak"
    _sh.copy("/root/influence/studio/taste-pairs.jsonl", _bak_p)
    _sh.copy("/root/influence/studio/taste-profile.json", _bak_j)
    try:
        from taste_profile import record_ranking, function_weights, chair_function
        assert chair_function("yuki", "veiled whisper female") == "whisper"
        assert chair_function("narrator", "calm male") == "narration"
        assert chair_function("lecturer", "") == "lecture"
        cards = [{"voice_id": "a", "tags": ["whisper", "soft", "female"]},
        {"voice_id": "b", "tags": ["loud", "energetic", "male"]}]
        r = record_ranking("whisper", ["a", "b"], cards)
        assert r["ok"] is True and r["pairs"] == 1
        w = function_weights("whisper")
        assert w.get("whisper", 0) > w.get("loud", 0)
        assert function_weights("nosuchfn") == {}
        assert record_ranking("x", ["only"])["ok"] is False
    finally:
        _sh.copy(_bak_p, "/root/influence/studio/taste-pairs.jsonl")
        _sh.copy(_bak_j, "/root/influence/studio/taste-profile.json")


def test_bt_fit_learns_and_predicts():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from bt_fit import (fit, p_beats, voice_features, profile_features,
                        verdict_from_margin)
    pairs = [
        {"winner": voice_features(["whisper", "soft", "female"], 2),
         "loser": voice_features(["loud", "energetic", "male"], 0)}
        for _ in range(6)
    ]
    r = fit(pairs)
    assert r["pairs"] == 6 and r["train_accuracy"] >= 0.9
    w = r["weights"]
    assert w.get("tag:whisper", 0) > w.get("tag:loud", 0)
    p = p_beats(voice_features(["whisper", "soft"], 1),
                voice_features(["loud"], 0), w)
    assert p > 0.5
    prof = profile_features({"modulator_range": ["smug"],
                             "age": "old", "archetype": "bisociation"})
    assert "want:smug" in prof and "want:old" in prof
    assert verdict_from_margin(3.5, 6) == {"state": "hot",
                                           "action": "double_down"}
    assert verdict_from_margin(-1.0, 2)["action"] == "pivot"


def test_next_character_picks_thinnest():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from taste_profile import next_character
    cands = [{"name": "A", "direction": "calm male", "dialogue_lines": 30},
             {"name": "B", "direction": "whisper female", "dialogue_lines": 5}]
    p = next_character(cands)
    assert p is not None and "why" in p and "function" in p
    locked = [dict(cands[0], locked=True), cands[1]]
    assert next_character(locked)["name"] == "B"
    assert next_character([]) is None


def test_propose_direction_override():
    import sys as _s
    _s.path.insert(0, "/root/influence/dash")
    _s.path.insert(0, "/root/influence/pipeline")
    import channel_onboard as ob
    assert ob.propose("folk-and-fable", "nosuchchair")["ok"] is False
    assert ob.propose("folk-and-fable", "nosuchchair",
                      direction="")["ok"] is False


def test_acoustics_cache_and_lies():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from voice_acoustics import tag_lies
    assert any("250" in x for x in tag_lies(["deep", "low"], {"f0_mean": 250, "f0_std": 40, "voiced": 0.6}))
    assert tag_lies(["calm"], {"f0_mean": 150, "f0_std": 40, "voiced": 0.5}) == []
    assert tag_lies([], {}) == []


def test_affect_selection_side():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from ensemble_cast import affect_for
    w = affect_for("witch", "", None)
    assert w["valence"] < 0 and w["power"] > 0
    assert "dark" in w["voice_words"] and "calm" in w["voice_words"]
    h = affect_for("fairy", "", None)
    assert h["valence"] > 0 and "warm" in h["voice_words"]
    r = affect_for(None, "", None)
    assert r["arousal"] <= -0.2  # sleep clamp holds everywhere


def test_archetype_classifier():
    import sys as _s
    _s.path.insert(0, "/root/influence/pipeline")
    from ensemble_cast import classify_archetype, oppose_band
    assert classify_archetype("Reptilian guard")["archetype"] == "beast"
    assert classify_archetype("Yuki", "whisper")["archetype"] == "fae"
    assert classify_archetype("Baba Yaga", "witch")["archetype"] == "crone"
    assert classify_archetype("Kai", "boy")["archetype"] == "innocent"
    assert classify_archetype("Xyzzy Qqq")["confidence"] == 0.0
    lo, hi = oppose_band((140, 220))
    assert hi < 140  # villain drops below hero band
    lo2, hi2 = oppose_band((90, 130))
    assert lo2 > 130  # villain floats above low hero band
