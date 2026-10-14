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
