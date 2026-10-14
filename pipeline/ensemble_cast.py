"""Ensemble casting — a whole book's cast, not isolated picks.

One voice per character per book (no repeats), contrast where the story
needs it (old/young, big/small, stern/kind), shared sleep warmth (every
voice must be calm-capable). Briefs answer "what should a tree sound
like?" from story info: role + size + age + function. Voice-design
instructions come out acoustic-rich (ab-prompt style): pitch band,
delivery, accent, sleep constraints.

Pure string logic (compose_cast) + network fill (fill_cast) kept separate
so tests stay offline.
"""
from __future__ import annotations

# size → pitch band (Hz, approximate, for design instructions)
_SIZE_BAND = [
    (("giant", "enormous", "huge", "troll", "ogre", "bear"), (70, 110)),
    (("king", "emperor", "old", "father", "grandfather"), (85, 130)),
    (("man", "male", "woodcutter", "soldier", "merchant"), (100, 150)),
    (("woman", "queen", "mother", "wife", "witch"), (150, 220)),
    (("young", "lad", "boy", "son", "youthful"), (140, 200)),
    (("girl", "lass", "daughter", "maiden", "princess"), (180, 260)),
    (("child", "kid", "baby", "little"), (200, 300)),
    (("mouse", "tiny", "bird", "fairy"), (220, 320)),
]

_FUNCTION_WORDS = {
    "trickster": ("fox", "cat", "spider", "anansi", "loki", "trick"),
    "helper": ("fairy", "godmother", "donor", "helper", "guide"),
    "villain": ("witch", "ogre", "troll", "giant", "wolf", "dragon"),
    "ruler": ("king", "queen", "emperor", "prince", "princess"),
    "everyman": ("woodcutter", "miller", "tailor", "soldier", "fisherman"),
}

_CALM_TAGS = ("calm", "soft", "gentle", "slow", "warm", "soothing",
              "narration", "storytelling", "mellow", "low")


def pitch_band(role: str | None, age: str | None,
               gender: str | None) -> tuple[int, int]:
    """Pitch band from story facts. Giants rumble, mice pipe."""
    import re as _re
    low = " ".join(x for x in [role or "", age or "", gender or ""] if x)
    for words, band in _SIZE_BAND:
        if any(_re.search(r"\b" + w + r"\b", low, _re.I) for w in words):
            return band
    if (gender or "").strip().lower() == "female":
        return (160, 240)
    return (100, 160)


def story_function(name: str, role: str | None) -> str:
    low = (name + " " + (role or "")).lower()
    for fn, words in _FUNCTION_WORDS.items():
        if any(w in low for w in words):
            return fn
    return "supporting"


# ---------- affect (MARY-compatible selection side) ----------
#
# Comedy lane calibrates DELIVERY from affect (their mary_model.json:
# arousal/valence/power -> rate/volume/range/pitch-direction). We solve
# the easier complementary problem, SELECTION: from story facts, estimate
# the affect coords a character's voice should carry, then match voices
# whose tags live in the same neighborhood. Same dims [-1,1], same
# vocabulary — the two lanes stay interoperable by construction.
# Sleep clamp: arousal never exceeds -0.2 here (sleep content); energy
# belongs to lore-variety lanes, not the selection model.

def affect_for(role: str | None, function: str = "",
               age: str | None = None) -> dict:
    """Story facts -> desired affect coords + voice words."""
    r, fn = (role or "").lower(), (function or "").lower()
    valence, power = 0.1, 0.0  # sleep baseline: mildly warm, no dominance
    if any(k in r + fn for k in ("witch", "villain", "ogre", "troll",
                                 "wolf", "dragon", "wicked", "cruel")):
        valence, power = -0.5, 0.6
    elif any(k in r + fn for k in ("king", "queen", "emperor", "ruler")):
        valence, power = 0.0, 0.7
    elif any(k in r + fn for k in ("helper", "fairy", "godmother", "mother",
                                   "guide", "mermaid", "maiden")):
        valence, power = 0.6, -0.2
    elif any(k in r + fn for k in ("trickster", "fox", "anansi", "cat",
                                   "spider")):
        valence, power = 0.3, 0.2
    elif any(k in r + fn for k in ("victim", "child", "lost", "poor",
                                   "orphan")):
        valence, power = -0.1, -0.5
    words = []
    words += ["warm", "kind", "gentle"] if valence > 0.2 else []
    words += ["dark", "cold", "menacing"] if valence < -0.2 else []
    words += ["deep", "commanding", "authoritative"] if power > 0.4 else []
    words += ["soft", "small", "meek"] if power < -0.3 else []
    words += ["calm", "slow", "soft"]  # sleep clamp, always
    return {"valence": valence, "power": power, "arousal": -0.5,
            "voice_words": sorted(set(words))}


def brief_character(char: dict) -> str:
    """What should this voice sound like? Answered from story info."""
    name = char.get("name", "?")
    role = char.get("role") or "figure"
    age = char.get("age") or "ageless"
    gender = char.get("gender") or "unspecified"
    fn = story_function(name, char.get("role"))
    lo, hi = pitch_band(char.get("role"), char.get("age"), char.get("gender"))
    bits = [f"{name}: {age} {gender} {role} ({fn})",
            f"pitch around {lo}-{hi}Hz"]
    aff = affect_for(char.get("role"), fn + " " + name)
    bits.append(f"affect v{aff['valence']}/p{aff['power']}: "
                f"{', '.join(aff['voice_words'][:6])}")
    if fn == "trickster":
        bits.append("quick, sly warmth — mischief, never menace")
    elif fn == "villain":
        bits.append("weight without shouting — dread, not volume")
    elif fn == "ruler":
        bits.append("unhurried authority — rooms quiet when they speak")
    elif fn == "helper":
        bits.append("soft light — relief whenever they arrive")
    else:
        bits.append("plain and kind — the sleep baseline")
    if char.get("dialogue_lines", 0) == 0:
        bits.append("rarely speaks — mentioned-voice, low priority")
    return "; ".join(bits)


def design_instruction_for(char: dict, context: str = "") -> str:
    """Acoustic-rich voice-design prompt (ab-prompt style) from profile."""
    lo, hi = pitch_band(char.get("role"), char.get("age"), char.get("gender"))
    fn = story_function(char.get("name", ""), char.get("role"))
    return (f"{fn.title()} character voice, "
            f"{char.get('age') or 'ageless'} {char.get('gender') or ''} "
            f"pitch around {(lo + hi) // 2}Hz within {lo}-{hi}Hz, "
            f"slow sleep pacing, soft consonants, calm and drowsy delivery "
            f"with gentle downward glides at sentence ends, never flat robotic, "
            f"never loud. For {context or 'sleep storytelling'}.")


def compose_cast(characters: list[dict], context: str = "",
                max_cast: int = 8) -> list[dict]:
    """Speaking characters by dialogue share → brief + query + instruction.
    Narrator (most lines, no role) reads as the backbone slot."""
    speaking = [c for c in characters if c.get("dialogue_lines", 0) > 0]
    speaking.sort(key=lambda c: -c["dialogue_lines"])
    cast = []
    for i, c in enumerate(speaking[:max_cast]):
        q = c.get("voice_query") or "calm narration"
        cast.append({"name": c["name"], "slot": i,
                     "narrator": i == 0 and not c.get("role"),
                     "brief": brief_character(c),
                     "voice_query": q,
                     "design_instruction": design_instruction_for(c, context),
                     "sample_line": c.get("sample_line", "")})
    return cast


def contrast_notes(cast: list[dict]) -> list[str]:
    """Ensemble sanity: flag same-band collisions the story can't afford."""
    notes = []
    # compare pairwise on query signature (cheap distinctness proxy)
    seen = {}
    for c in cast:
        sig = c["voice_query"]
        if sig in seen:
            notes.append(f"{c['name']} and {seen[sig]} share query "
                         f"'{sig}' — force contrast (age/size axis)")
        else:
            seen[sig] = c["name"]
    return notes
