"""Character delivery-spec -> voice profile (the adapter).

Ownership: prx0r/characters owns ALL delivery truth (modulators with
arousal/valence/power, MARY knobs, vibe phrases, restraint rules,
interview style, register). This module owns nothing but the mapping:
full character.json in -> voice profile out.

Explicitly NOT mapped: comedy.* (operator_priors are joke operators,
not voice), philosophy (worldview, not vocal), memories/threads
(plot, not voice). Those stay on their side.

Usage:
  python3 pipeline/character_to_voice.py reptilian-ralph-middle-management
  python3 pipeline/character_to_voice.py --all
"""
from __future__ import annotations

import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # dash modules (ensemble_cast)
sys.path.insert(0, _HERE)  # pipeline modules

CHARACTERS = "/root/characters"
MODULATORS_PATH = os.path.join(CHARACTERS, "audition", "modulators.json")
MARY_PATH = os.path.join(CHARACTERS, "audition", "voicelab", "mary_model.json")
FREAKS = os.path.join(CHARACTERS, "freaks")

# vibe -> delivery phrase: THEIR table (voicecast.VIBE_DELIVERY), imported
# when available so wording never drifts; minimal fallback otherwise.
_FALLBACK_VIBE = {
    "deadpan": "flat deadpan delivery, minimal pitch movement, dry",
    "manic": "fast kinetic delivery, wide pitch swings, barely contained energy",
    "smug": "slow savoring delivery, pleased with every word",
    "exhausted": "low-energy delivery, barely finding the energy to finish",
    "relaxed": "easy unhurried delivery, casual warmth",
}


def _vibe_table() -> dict:
    try:
        sys.path.insert(0, os.path.join(CHARACTERS, "audition"))
        from voicecast import VIBE_DELIVERY as _vd
        return dict(_vd)
    except Exception:
        return dict(_FALLBACK_VIBE)


def _load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def modulator_aggregate(modulator_range: list) -> dict:
    """Modulator names -> mean affect + mean performative deltas.

    Unmapped names (their table doesn't have them, e.g. annoyed,
    confused) are reported, never silently dropped.
    """
    mods = _load_json(MODULATORS_PATH)
    aff = {"arousal": [], "valence": [], "power": []}
    perf = {"pace_delta": [], "pause_mult": [], "emphasis_delta": []}
    used, unmapped = [], []
    for m in modulator_range or []:
        spec = mods.get(str(m).lower())
        if not spec:
            unmapped.append(str(m))
            continue
        used.append(str(m))
        emo = spec.get("emotional", {})
        for k in aff:
            if isinstance(emo.get(k), (int, float)):
                aff[k].append(float(emo[k]))
        per = spec.get("performative", {})
        for k in perf:
            if isinstance(per.get(k), (int, float)):
                perf[k].append(float(per[k]))
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else 0.0
    return {
        "used": used,
        "unmapped": unmapped,
        "affect": {k: mean(v) for k, v in aff.items()},
        "performative": {k: mean(v) for k, v in perf.items()},
    }


def mary_knobs(affect: dict) -> dict:
    """MARY rules (their mary_model.json) applied to aggregate affect."""
    ar, va = float(affect.get("arousal", 0.0)), float(affect.get("valence", 0.0))
    return {
        "rate_delta": round(0.5 * ar + 0.2 * va, 3),
        "volume_db": round(6.6 * ar, 2),
        "range_st": round(4 + 4 * ar, 2),
        "pitch_direction": "falling" if va < 0 else ("rising" if va > 0 else "flat"),
        "source": "mary_model.json rules on modulator-mean affect",
    }


def map_pack(slug: str) -> dict:
    """Full character.json -> voice profile. Pure read of their files."""
    path = os.path.join(FREAKS, slug, "character.json")
    try:
        with open(path, encoding="utf-8") as f:
            pack = json.load(f)
    except OSError:
        return {"ok": False, "reason": f"no pack {slug}"}

    from ensemble_cast import classify_archetype  # noqa: E402

    persona = pack.get("persona", {}) or {}
    profile = pack.get("profile", {}) or {}
    expression = pack.get("expression", {}) or {}
    vibe = str(pack.get("vibe") or "").lower()
    delivery_phrase = _vibe_table().get(vibe, _vibe_table().get("relaxed", ""))

    agg = modulator_aggregate(pack.get("modulator_range") or [])
    affect = agg["affect"]
    knobs = mary_knobs(affect)

    # pitch: their species/canon/persona -> our archetype table (backstop
    # only; packs carry no numeric pitch of their own).
    arch = classify_archetype(
        pack.get("name", ""),
        " ".join([str(pack.get("species", "")), str(pack.get("canon", "")),
                  str(persona.get("interview_style", ""))]))
    aprof = arch.get("profile", {}) if arch.get("confidence", 0) > 0 else {}

    # vibe missing/unknown (e.g. Baba: empty vibe): fall back to the
    # archetype delivery, never to a wrong-but-pleasant default.
    if vibe not in _vibe_table() and aprof.get("delivery"):
        delivery_phrase = aprof["delivery"] + " (via archetype; pack vibe empty)"
        vibe_fallback = True
    else:
        vibe_fallback = False

    pace = float(profile.get("pace", 0.8) or 0.8)
    pace_adj = pace + agg["performative"].get("pace_delta", 0.0)
    pace_w = ("fast urgent pacing" if pace_adj >= 0.85 else
              "measured pacing" if pace_adj >= 0.55 else "slow deliberate pacing")
    energy = float(profile.get("energy", 0.5) or 0.5)
    energy_w = ("high-energy" if energy >= 0.75 else
                "mid-energy" if energy >= 0.45 else "low-energy")

    register = str(expression.get("default_register", "") or "")
    restraint = str(expression.get("emotional_restraint", "") or "").lower()
    restraint_note = ""
    if restraint == "high":
        restraint_note = ("high restraint: emotion pressed flat, "
                          "leaks at the edges, never shouts")
    elif restraint == "low":
        restraint_note = "low restraint: feelings out loud, no filter"

    interview = str(persona.get("interview_style", "") or "")
    deal = str(persona.get("deal", "") or "")
    direction = " ".join(p for p in [
        f"{pack.get('name', slug)}: {deal}"[:220],
        f"Speaks {interview}." if interview else "",
        f"Voice: {energy_w}, {pace_w}. {delivery_phrase}.",
        f"Register: {register}." if register else "",
        restraint_note,
    ] if p)

    words: list[str] = []
    for bit in [delivery_phrase, interview, register,
                " ".join(agg["used"]), str(aprof.get("delivery", ""))]:
        for w in str(bit).lower().replace(",", " ").split():
            w = "".join(c for c in w if c.isalpha())
            if len(w) >= 4 and w not in words:
                words.append(w)

    return {
        "ok": True,
        "pack": slug,
        "voice_profile": {
            "pitch_hz": list(aprof.get("pitch", (100, 160))),
            "pitch_source": f"archetype:{arch.get('archetype')} "
                            f"(conf {arch.get('confidence')})" if arch.get("confidence") else "default",
            "pace": {"pack": pace, "modulator_adjusted": round(pace_adj, 3),
                     "words": pace_w},
            "energy": {"pack": energy, "words": energy_w},
            "delivery": ". ".join(p for p in
                                  [delivery_phrase, restraint_note] if p),
            "affect": affect,
            "mary": knobs,
            "register": register,
            "restraint": restraint or "unspecified",
            "voice_words": words[:24],
            "direction": direction[:800],
            "hold_ms": profile.get("punchline_hold_ms"),
        },
        "modulators_used": agg["used"],
        "modulators_unmapped": agg["unmapped"],
        "sources": {"modulators": "audition/modulators.json",
                    "mary": "audition/voicelab/mary_model.json",
                    "vibe": "audition/voicecast.py VIBE_DELIVERY",
                    "pitch": "pipeline/ensemble_cast.py ARCHETYPES"},
    }


def main() -> None:
    args = sys.argv[1:]
    if args == ["--all"]:
        slugs = sorted(os.path.basename(d) for d in
                       glob.glob(os.path.join(FREAKS, "*"))
                       if os.path.isfile(os.path.join(d, "character.json")))
    else:
        slugs = args or ["reptilian-ralph-middle-management"]
    for slug in slugs:
        print(json.dumps(map_pack(slug), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
