"""Tests for audio_flow + new audio.* MCP/pi tools. No network, no spend.

Live paths are tested fail-closed only (no grant → refusal). Real Fish MCP
calls are infra-verified manually ($0 reads), never in the suite.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from audio_flow import tts_quote, speak, generate_media, estimate_media


def test_tts_quote_pure_math():
    q = tts_quote("hello")
    assert q["bytes"] == 5 and q["credits"] == 5
    q2 = tts_quote("héllo")  # multibyte: é = 2 bytes
    assert q2["bytes"] == 6 and q2["credits"] == 6
    q3 = tts_quote("hi", pro_clone_2x=True)
    assert q3["credits"] == 4 and q3["multiplier"] == 2


def test_speak_dryrun_pure():
    r = speak("Hello world", "voice-123")
    assert r["ok"] is True and r["dry_run"] is True
    assert r["quote"]["bytes"] == 11 and r["quote"]["credits"] == 11
    assert r["payload_hash"].startswith("sha256:")
    assert "grant" in r["next"]
    # missing args refuse
    assert speak("", "v")["ok"] is False
    assert speak("hi", "")["ok"] is False


def test_speak_live_fails_closed_without_grant():
    r = speak("Hello", "voice-123", dry_run=False)
    assert r["ok"] is False and "FAIL CLOSED" in r["reason"]
    r2 = speak("Hello", "voice-123", dry_run=False, ctx={})
    assert r2["ok"] is False


def test_generate_media_rejects_bad_kind():
    r = estimate_media("audio", "ws", "m", "p")
    assert r["ok"] is False and "image|video" in r["reason"]


def test_generate_media_live_fails_closed_without_grant():
    r = generate_media("image", "ws", "m", "a cat", 500, dry_run=False)
    assert r["ok"] is False and "FAIL CLOSED" in r["reason"]


def test_mcp_registers_audio_tools():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "dash"))
    import mcp as dash_mcp
    names = {t["name"] for t in dash_mcp.TOOLS}
    for n in ("audio.voices", "audio.balance", "audio.speak",
              "audio.estimate", "audio.generate"):
        assert n in names, n


def test_pi_allowlists_audio_reads_only():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "dash"))
    import agent_chat
    assert "audio.voices" in agent_chat.READONLY_TOOLS
    assert "audio.balance" in agent_chat.READONLY_TOOLS
    assert "audio.estimate" in agent_chat.READONLY_TOOLS
    # spend tools stay OUT of pi's reach
    assert "audio.speak" not in agent_chat.READONLY_TOOLS
    assert "audio.generate" not in agent_chat.READONLY_TOOLS


def test_costs_cover_fish():
    sys.path.insert(0, os.path.dirname(_HERE))
    from pipeline.costs import COSTS_USD
    assert COSTS_USD["fish.tts_byte"] == 0.0
    assert COSTS_USD["fish.media_job"] == 0.0
    assert COSTS_USD["fish.read"] == 0.0


def test_runtime_guard_exempts_audio_flow():
    from pipeline.runtime import guard_imports
    bad = [v for v in guard_imports() if "audio_flow" in v]
    assert bad == [], bad
