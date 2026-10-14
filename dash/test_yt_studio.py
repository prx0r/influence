"""YT studio loop: knobs clamp, vibe rules, formula round-trip, preview
render through render_pilot with the free TTS stubbed (no network, $0)."""
import json
import os
import shutil
import sys
import tempfile
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
if not os.access(os.environ.get("SLEEPDRAW_DIR", "/root/sleepdraw"),
                 os.W_OK) and not os.access("/root", os.W_OK):
    # CI / sandbox without the owner's /root tree
    os.environ["SLEEPDRAW_DIR"] = tempfile.mkdtemp(prefix="sleepdraw-")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    import sleep_studio as st
    import yt_studio as yt
    damn = tmp_path / "damn"
    pil = damn / "projects" / "folk-and-fable" / "pilots"
    pil.mkdir(parents=True)
    (damn / "fish").mkdir()
    (damn / "fish" / "gate.py").write_text(
        "def gate(t):\n    return {'pass': True}\n")
    (damn / "fish" / "tts-poison.py").write_text(
        "def poison(t):\n    return {'pass': True}\n")
    drama = pil / "01-test.drama.txt"
    drama.write_text(
        "// narrator <|speaker:0|> Adrian bf322df2096a46f18c579d0baa36f41d\n"
        "<|speaker:0|> The snow fell softly on the quiet village. "
        "Nobody stirred. The fire burned low and warm.\n"
        "<|speaker:0|> In the morning the doorway was open, and the "
        "path led up into the white hills.\n")
    voice = tmp_path / "voice"
    voice.mkdir()
    chan = tmp_path / "channels"
    shutil.copytree(os.path.join(HERE, "..", "studio", "channels"), chan)
    monkeypatch.setattr(st, "DAMN", str(damn))
    monkeypatch.setattr(st, "VOICE", str(voice))
    monkeypatch.setattr(yt, "CHAN_DIR", str(chan))
    calls = []

    class AF:
        @staticmethod
        def speak_free(text, vid, out_path="", speed=1.0, volume_db=0.0,
                       temperature=None):
            calls.append({"speed": speed, "temperature": temperature,
                          "vid": vid})
            # 0.2s of silent mp3 via ffmpeg so concat is real
            os.system(f"ffmpeg -loglevel quiet -y -f lavfi -i anullsrc=r=22050:cl=mono "
                      f"-t 0.2 -q:a 9 {out_path}")
            return {"ok": True}
    monkeypatch.setattr(st, "_audio_flow", lambda: AF)
    return {"st": st, "yt": yt, "drama": str(drama), "calls": calls}


def test_clean_knobs_clamps_and_drops_junk():
    import yt_studio as yt
    k = yt.clean_knobs({"speed": 9, "temperature": -3, "volume_db": 40,
                        "preview_segments": 0, "evil": 1,
                        "voices": {"narrator": "not-an-id",
                                   "yuki": "b347db033a6549378b48d00acb0d06cd"}})
    assert k["speed"] == 2.0 and k["temperature"] == 0.0
    assert k["volume_db"] == 6.0 and k["preview_segments"] == 1
    assert "evil" not in k
    assert k["voices"] == {"yuki": "b347db033a6549378b48d00acb0d06cd"}


def test_rule_vibe_intents():
    import yt_studio as yt
    base = {"speed": 0.85, "temperature": 0.7, "voices": {}}
    chairs = [{"name": "yuki", "options": [
        {"id": "b347db033a6549378b48d00acb0d06cd", "label": "Selene 595k"}]}]
    r = yt.rule_vibe("bit slower and calmer", base, chairs)
    assert r["intent"] == "retake" and r["knobs"]["speed"] < 0.85
    assert r["knobs"]["temperature"] < 0.7
    r = yt.rule_vibe("use selene for yuki", base, chairs)
    assert r["knobs"]["voices"]["yuki"].startswith("b347")
    assert yt.rule_vibe("ok render the full thing", base, chairs)[
        "intent"] == "render_full"
    assert yt.rule_vibe("ok render full", base, chairs)["intent"] == "render_full"
    assert yt.rule_vibe("save this formula", base, chairs)[
        "intent"] == "save_formula"
    assert yt.rule_vibe("what's the cadence?", base, chairs)["intent"] == "chat"


def test_formula_round_trip(env):
    yt = env["yt"]
    r = yt.save_formula("folk-and-fable", {"speed": 0.8}, "take-x.mp3",
                        "hushed", ["The {X} Who Slept"])
    assert r["ok"] and r["formula"]["version"] == 1
    r2 = yt.save_formula("folk-and-fable", {"speed": 0.78})
    assert r2["formula"]["version"] == 2
    assert r2["formula"]["titles"] == ["The {X} Who Slept"]
    assert r2["formula"]["history"][-1]["knobs"]["speed"] == 0.8
    with pytest.raises(ValueError):
        yt.save_formula("../etc", {})


def test_preview_take_renders_with_knobs(env):
    yt, calls = env["yt"], env["calls"]
    v = yt.channel_view("folk-and-fable")
    assert [p["file"] for p in v["pilots"]] == ["01-test.drama.txt"]
    r = yt.start_take(env["drama"], "folk-and-fable",
                      {"speed": 0.77, "temperature": 0.4,
                       "preview_segments": 1})
    assert r["ok"]
    for _ in range(100):
        j = yt.job(r["job"])
        if j["status"] != "running":
            break
        time.sleep(0.1)
    assert j["status"] == "done", j
    assert j["result"]["take_kind"] == "preview"
    assert calls and all(c["speed"] == 0.77 and c["temperature"] == 0.4
                         for c in calls)
    # preview stops at 1 segment
    assert len(j["result"]["pilot"]["segments"]) == 1
    takes = yt.channel_view("folk-and-fable")["takes"]
    assert takes and takes[0]["knobs"]["speed"] == 0.77


def test_take_rejects_path_outside_damn(env):
    with pytest.raises(ValueError):
        env["yt"].start_take("/etc/passwd", "folk-and-fable", {})
