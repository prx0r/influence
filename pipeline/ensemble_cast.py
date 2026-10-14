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


# ---- archetype voice table (research-grounded selection) ----
#
# Sources: anime MRI study (heroes open/breathy, villains-M constricted,
# villains-F lowered-larynx), Evil-Sounds-Deep vs Creepy-High split
# (big/powerful evil = deep; small/sneaky/fair-folk evil = high),
# anime 3 P's per archetype (pitch/pace/projection), opera tessitura
# opposition (villain takes highest OR lowest vs hero range).
# This is the Jev-style typed classifier: archetype in -> voice profile
# out (pitch band, pace, projection, delivery). Deterministic now;
# model-judged later. Same dims as MARY (arousal/valence/power).

ARCHETYPES = {
    # big evil: deep, harsh, commanding, slow (Vader/Scar/Overlord)
    "overlord": {"pitch": (70, 110), "pace": "slow", "projection": "commanding",
                 "delivery": "deep, harsh edge, unhurried menace",
                 "valence": -0.6, "power": 0.9, "arousal": -0.1},
    # sneaky evil: high, nasal, quick (imps, goblins, fair folk, Joker)
    "imp": {"pitch": (200, 320), "pace": "quick", "projection": "nasal",
            "delivery": "bright, sly, giggling undercurrent",
            "valence": -0.4, "power": -0.2, "arousal": 0.5},
    # hero: open, breathy, bright, grounded (audience anchor)
    "hero": {"pitch": (140, 220), "pace": "even", "projection": "bright-forward",
             "delivery": "open throat, grounded, conversational courage",
             "valence": 0.5, "power": 0.3, "arousal": 0.2},
    # mentor: warm + weight, calm authority (sensei lane)
    "mentor": {"pitch": (90, 150), "pace": "slow", "projection": "warm-weight",
               "delivery": "warm and weighty, tragic patience",
               "valence": 0.4, "power": 0.5, "arousal": -0.4},
    # ethereal: high, breathy, light (fairies, spirits, fae)
    "fae": {"pitch": (200, 300), "pace": "drifting", "projection": "breathy-light",
            "delivery": "airy, veiled, half-smiling detachment",
            "valence": 0.2, "power": -0.4, "arousal": -0.3},
    # crone/witch: low female, textured, knowing (Yubaba split: shrill OR alto)
    "crone": {"pitch": (130, 200), "pace": "measured", "projection": "textured",
              "delivery": "knowing, dry, amused at mortals",
              "valence": -0.2, "power": 0.5, "arousal": -0.3},
    # beast/creature: big, resonant, simple (reptilian lane)
    "beast": {"pitch": (70, 120), "pace": "heavy", "projection": "resonant",
              "delivery": "massive and simple, pauses like weather",
              "valence": -0.1, "power": 0.8, "arousal": -0.2},
    # trickster: quick, sly, musical (Anansi, fox, Loki-lite)
    "trickster": {"pitch": (150, 250), "pace": "quick", "projection": "musical",
                  "delivery": "sly musicality, delight in the game",
                  "valence": 0.3, "power": 0.1, "arousal": 0.4},
    # innocent: high, small, plain (children, lambs, first-timers)
    "innocent": {"pitch": (220, 320), "pace": "plain", "projection": "small-clear",
                 "delivery": "plain wonder, no craft, all sincerity",
                 "valence": 0.5, "power": -0.5, "arousal": 0.0},
    # elder: low, slow, rooted (trees, ancients, mountains that talk)
    "elder": {"pitch": (80, 130), "pace": "rooted", "projection": "low-vast",
              "delivery": "geological patience, words like sediment",
              "valence": 0.1, "power": 0.6, "arousal": -0.5},
}

# ---- archetype -> catalogue tag vocabulary (the translation layer) ----
#
# Theory words (geological, sediment) never appear in Fish tags. These are
# the tag-vocabulary equivalents per archetype — what a voice OF this type
# is actually tagged by vendors. Scored directly in propose() so the
# prediction carries points, not just keywords.
ARCHETYPE_TAGS = {
    "overlord": ("deep", "dark", "commanding", "villain", "low", "slow"),
    "imp": ("playful", "young", "quick", "bright", "nasal", "high"),
    "hero": ("bright", "clear", "confident", "warm", "young", "strong"),
    "mentor": ("warm", "deep", "calm", "wise", "old", "slow"),
    "fae": ("soft", "gentle", "airy", "light", "female", "whisper"),
    "crone": ("old", "female", "dry", "knowing", "textured", "slow"),
    "beast": ("deep", "low", "slow", "resonant", "calm", "male"),
    "trickster": ("playful", "quick", "clever", "young", "musical", "bright"),
    "innocent": ("young", "soft", "clear", "gentle", "small", "female"),
    "elder": ("deep", "old", "slow", "low", "calm", "measured"),
}

# ---- archetype subtypes (criteria granularity) ----
#
# One tag set per archetype crowns one voice per archetype (Calm Sleep
# ruling 34 collections). Subtypes split by story vibe: a kwaidan elder
# (grave restraint) is acoustically distinct from a grimm elder (warm
# roundness) or an edda elder (projected weight). Vibe selects subtype.
ARCHETYPE_SUBTYPES = {
    "elder": {
        "grave": {"vibes": ("scary", "grim", "winter"),
                  "tags": ("deep", "low", "slow", "dark", "dry", "hollow"),
                  "pitch": (70, 120), "pace": "rooted",
                  "delivery": "grave restraint, cold tale told warmly flat"},
        "warm": {"vibes": ("sleepy", "romantic", "playful"),
                 "tags": ("warm", "round", "gentle", "affectionate", "soft",
                           "kind"),
                 "pitch": (90, 150), "pace": "unhurried",
                 "delivery": "hearth warmth, affectionate roundness"},
        "epic": {"vibes": ("epic", "magical"),
                 "tags": ("weighty", "vast", "commanding", "resonant",
                           "unhurried", "deep"),
                 "pitch": (80, 130), "pace": "monumental",
                 "delivery": "projected weight, rooms quiet when they speak"},
    },
    "fae": {
        "veiled": {"vibes": ("scary", "winter", "grim"),
                   "tags": ("veiled", "still", "quiet", "pale", "distant",
                             "cold"),
                   "pitch": (180, 260), "pace": "drifting",
                   "delivery": "still veiled cold, half-smiling detachment"},
        "wonder": {"vibes": ("magical", "romantic", "sleepy", "playful",
                             "epic"),
                   "tags": ("bright", "lilting", "curious", "light",
                             "enchanted", "warm"),
                   "pitch": (200, 300), "pace": "lilting",
                   "delivery": "bright curiosity, enchanted lift"},
    },
}


def subtype_for(archetype: str, vibes: list) -> dict | None:
    """Story vibes -> subtype profile. None when archetype has no splits.
    Subtype tags UNION the base archetype tags (vendors tag old/calm,
    never hollow/dry — pure-theory vocabularies match nothing)."""
    subs = ARCHETYPE_SUBTYPES.get(archetype or "")
    if not subs:
        return None
    vl = [str(v).lower() for v in vibes]
    for _name, sub in subs.items():
        if any(v in vl for v in sub["vibes"]):
            base = list(ARCHETYPE_TAGS.get(archetype, ()))
            tags = base + [t for t in sub["tags"] if t not in base]
            return dict(sub, name=_name, tags=tags)
    return None


_ARCHETYPE_KEYS = {
    "overlord": ("giant", "overlord", "emperor", "sorcerer", "darth", "scar",
                 "evil chancellor", "don", "brute", "troll-", "ogre", "dragon"),
    "imp": ("imp", "goblin", "clown", "joker", "gnome", "banshee", "siren",
            "gremlin", "anansi", "fox", "spider", "trick"),
    "hero": ("hero", "prince", "knight", "protagonist", "minokichi"),
    "mentor": ("mentor", "sensei", "master", "sage", "guide", "father",
               "grandfather", "keeper", "tender", "referee"),
    "fae": ("fairy", "fae", "elf", "spirit", "yuki", "mermaid", "sylph",
            "wonder", "scheherazade", "beguiling"),
    "crone": ("witch", "crone", "hag", "baba", "yaga", "yubaba", "stepmother"),
    "beast": ("reptilian", "beast", "dragon", "bear", "wolf", "lion",
              "serpent", "crocodile", "lizard"),
    "trickster": ("trickster", "fox", "anansi", "cat", "raven", "coyote", "tiger", "monkey"),
    "innocent": ("child", "kid", "baby", "lamb", "kai", "gerda", "lad",
                 "apprentice"),
    "elder": ("tree", "oak", "ancient", "mountain", "ent", "tortoise",
              "grandmother", "grandfather", "ghost", "grave", "tomb",
              "crypt", "ancestor", "elder", "storyteller", "skald",
              "griot", "bard", "authority", "weight", "winter"),
}


def classify_archetype(name: str, role: str | None = None,
                       tags: list | None = None) -> dict:
    """Character description -> archetype voice profile (the Jev-style
    typed decision: choice of archetype with pitch/pace/projection).
    Returns {archetype, profile, confidence, why}. Unknown -> {} default."""
    import re as _re2
    text = f"{name} {role or ''} {' '.join(tags or [])}".lower()
    scored = []
    for arch, keys in _ARCHETYPE_KEYS.items():
        hits = [k for k in keys if _re2.search(r"\b" + _re2.escape(k) + r"\b", text)]
        if hits:
            scored.append((len(hits), arch, hits))
    if not scored:
        return {"archetype": "supporting", "confidence": 0.0,
                "profile": {"pitch": (100, 200), "pace": "even",
                            "projection": "plain",
                            "delivery": "unmarked sleep narration",
                            "valence": 0.1, "power": 0.0, "arousal": -0.4},
                "why": "no archetype keywords — neutral sleep voice"}
    scored.sort(reverse=True)
    n, arch, hits = scored[0]
    total = sum(s[0] for s in scored)
    return {"archetype": arch, "confidence": round(min(0.95, n / max(1, total) + 0.3), 2),
            "profile": ARCHETYPES[arch],
            "why": f"matched {hits} → {arch} ({ARCHETYPES[arch]['delivery']})"}


def oppose_band(hero_band: tuple[int, int], villainous: bool = True) -> tuple[int, int]:
    """Opera tessitura rule: the villain takes highest OR lowest vs the
    hero range — never the same band (vocal dissonance reads as threat)."""
    lo, hi = hero_band
    mid = (lo + hi) / 2
    if not villainous:
        return hero_band
    # pick the farther extreme: below for menace-with-weight, above for
    # unhinged/small evil (director's choice recorded in reason)
    if mid >= 160:
        return (max(60, lo - 60), max(80, lo - 10))
    return (hi + 10, hi + 80)
