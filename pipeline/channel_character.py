"""Channel-as-character — every log channel becomes a reader.

A channel record (studio/channels/<slug>.json) already holds chairs with
locked voice IDs. This module compiles them into:
  1. per-chair Drama direction strings (sleep-native version of
     characters' modulator→direction compiler: base_direction +
     never-list + pace/bed context, sincerity-safe — delivery only)
  2. an SDK-compatible seed shape (philosophy/problem_space/modulators)
     so bgraph2/characters can adopt the channel later without rework
  3. a multi-speaker roster for duels (narrator + chairs in one request)

Channels read logs; personas make them distinct. Same content, new person.
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS_DIR = os.path.normpath(os.path.join(_HERE, "..", "studio", "channels"))


def load_channel(slug: str) -> dict:
    if not slug.replace("-", "").replace("_", "").isalnum():
        raise OSError(f"bad slug {slug!r}")
    p = os.path.join(CHANNELS_DIR, slug + ".json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def compile_direction(chair: dict, channel: dict | None = None) -> str:
    """Chair dict → Drama 3 direction string. Delivery only, never comedy
    winks, never plot — the sincerity rule, sleep edition."""
    parts = [chair.get("direction", "").strip("[]")]
    never = chair.get("never") or []
    if never:
        parts.append("never " + ", ".join(never[:3]))
    pace = ((channel or {}).get("voice") or {}).get("pace")
    if pace and pace != 1.0:
        parts.append("slower than normal speech" if pace < 1.0
                     else "brisker than normal speech")
    out = ", ".join(p for p in parts if p)
    return f"[{out}]" if out else ""


def roster_for_duel(channel: dict, scene_chairs: list[str]) -> dict:
    """Map chair names → locked fish voice IDs for a multi-speaker scene.
    Raises on unlocked chairs (no silent fallback voices)."""
    chairs = (channel.get("voice") or {}).get("chairs", {})
    roster = {}
    for name in scene_chairs:
        c = chairs.get(name) or {}
        vid = c.get("fish_id") or (c.get("candidates") or [{}])[0].get("id", "")
        if not vid:
            raise ValueError(f"chair '{name}' has no locked voice — "
                             f"ear-check first, then lock the ID")
        roster[name] = vid
    return roster


def to_seed(channel: dict) -> dict:
    """SDK-compatible character seed for a channel. bgraph2/characters can
    adopt verbatim: seed stays versioned, instances/edges append later."""
    slug = channel.get("channel", "unknown")
    chairs = (channel.get("voice") or {}).get("chairs", {})
    return {
        "schema_version": "character-graph.v1",
        "character_id": f"channel-{slug}",
        "name": channel.get("display_name", slug),
        "kind": "channel",
        "status": channel.get("status", "pilot"),
        "seed": {
            "philosophy": {
                "orientation": [channel.get("pitch", "")],
                "problem_space": ["sleep induction via narrative"],
            },
            "modulator_range": ["calm", "measured", "drowsy", "warm"],
            "canon": f"studio/channels/{slug}.json",
            "seed_version": 1,
        },
        "who": {"chairs": {
            name: {"label": (c.get("label") or ""),
                   "direction": compile_direction(c, channel),
                   "voice_id": (c.get("fish_id") or "")}
            for name, c in chairs.items()}},
        "profile": {
            "voice": f"roster of {len(chairs)} locked chairs",
            "branches": [{"branch_id": "youtube", "platform": "youtube",
                          "enabled": True,
                          "account": {"handle": "",
                                      "status": "unclaimed"}}],
        },
        "instances": [],
        "edges": [],
        "analytics": {},
        "provenance": ["influence studio/channels", channel.get("engine", "")],
    }


def save_seed(slug: str) -> str:
    """Compile + write <slug>.seed.json next to the channel record."""
    ch = load_channel(slug)
    out = os.path.join(CHANNELS_DIR, slug + ".seed.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(to_seed(ch), f, indent=1, ensure_ascii=False)
    return out
