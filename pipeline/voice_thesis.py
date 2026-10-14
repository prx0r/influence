#!/usr/bin/env python3
"""Voice thesis per channel: narrator-per-collection + per-character
predictions with whys, ready for owner ranking (ranks -> BT pairs).

F&F: 44 collections get vibe+tradition+narrator prediction from their
dramatis; chairs + top speaking characters get full theses.
Other channels (no dramatis): per-chair thesis from pitch+direction.
Known-voice shortlists come from LOCAL anchors/locks only (no API).

Usage: python3 pipeline/voice_thesis.py [--channel slug]
Output: studio/voice-thesis/<slug>.json
"""
import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/root/influence/dash")

OUT = "/root/influence/studio/voice-thesis"
CHAN = "/root/influence/studio/channels"

# slug/name signals -> story vibe (with weights for evidence order)
_VIBE_KEYS = {
    "scary": ("kwaidan", "yuki", "ghost", "demon", "snow-queen", "changeling",
              "haunt", "yurei", "vampire", "were-wolf", "witch"),
    "grim": ("witchcraft", "discoverie", "werewolf-case", "trials",
             "demonology", "household-spirits"),
    "playful": ("anansi", "aesop", "jamaica", "trick", "monkey", "tiger",
                "west-african", "fool", "simpleton"),
    "magical": ("fairy", "mermaid", "goblin", "arabian", "nights", "sinbad",
                "genie", "wish", "celtic", "keightley"),
    "epic": ("edda", "bulfinch", "bough", "mythology", "poetic", "prose-edd",
             "cyclops", "orpheus"),
    "romantic": ("aoyagi", "princess", "mermaid", "sleeping", "bride"),
    "winter": ("snow", "russian", "slav", "frost", "yuki", "yedo"),
}

_TRADITION_KEYS = {
    "Japanese folklore": ("kwaidan", "yuki", "japan", "aoyagi"),
    "West African folklore": ("anansi", "jamaica", "west-african", "tiger", "tacoomah"),
    "Russian folklore": ("russian", "slav", "baba", "skazka", "marusia", "afanasief"),
    "Norse myth": ("edda", "poetic", "prose"),
    "Greek/Classical myth": ("bulfinch", "cyclops", "orpheus", "sinbad", "bough"),
    "British Isles fairy": ("celtic", "keightley", "jacobs", "english-fairy", "west-england"),
    "Danish fairytale": ("andersen", "mermaid", "snow-queen", "emperor"),
    "German fairytale": ("grimm", "baba"),
    "French/Scheherazade": ("arabian", "nights", "thousand"),
}

# vibe -> narrator prediction (the theory, stated plainly)
_NARRATOR = {
    "scary": {"voice": "old, male, slow, low, grave-but-safe",
              "why": "fear content needs a hearth voice: dread in the tale, "
                     "safety in the teller. Falling pitch, warm floor, never loud."},
    "grim": {"voice": "ledger patience, distance, low and dry (either gender)",
             "why": "trials/demons told flat read as record, not threat. "
                    "Distance is the safety signal."},
    "playful": {"voice": "warm elder referee, sly, measured, amused",
                "why": "trickster casts are fast and loud; the narrator is the "
                       "frame, not a second picture. Amusement without competing."},
    "magical": {"voice": "soft wonder, airy but grounded, gentle lift",
                "why": "magic needs belief; belief needs warmth. Light on top, "
                       "weight underneath so it never floats away."},
    "epic": {"voice": "unhurried authority, weight, rooms quiet when they speak",
             "why": "myth is told by time itself. Slowness IS the grandeur; "
                    "haste would shrink it."},
    "romantic": {"voice": "tender, close, unhurried, smiling underneath",
                 "why": "love tales are told leaning in. Closeness, not projection."},
    "winter": {"voice": "oldest and weightiest, ledger patience, cold tale/warm teller",
               "why": "winter tales are told by winter itself; the teller's age "
                      "is the tale's age. Cold in the story, warm in the voice."},
    "sleepy": {"voice": "calm measured storyteller, slow and gentle",
               "why": "default sleep baseline: no spikes, no demands, pure carrier wave."},
}


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _anchors():
    d = _load(os.path.join(CHAN, "..", "voice-anchors.json"))
    return d if isinstance(d, list) else []


def sounds_like(voice_words):
    """Local anchors whose tags meet the predicted words. Evidence, not rank."""
    vw = set(str(w).lower() for w in voice_words)
    out = []
    for a in _anchors():
        tags = set(str(t).lower() for t in (a.get("tags") or []) +
                   (a.get("descriptors") or []))
        hit = sorted(vw & tags)
        if len(hit) >= 2:
            out.append({"voice": a.get("title"), "shared": hit[:5]})
    out.sort(key=lambda o: -len(o["shared"]))
    return out[:2]


def vibe_of(slug, top_names):
    text = (slug + " " + " ".join(top_names)).lower()
    found = []
    for vibe, keys in _VIBE_KEYS.items():
        hits = [k for k in keys if k in text]
        if hits:
            found.append((vibe, hits))
    if not found:
        return [("sleepy", ["baseline"])]
    return found


def tradition_of(slug):
    low = slug.lower()
    for trad, keys in _TRADITION_KEYS.items():
        if any(k in low for k in keys):
            return trad
    return "general tale stock"


def collection_thesis(slug, dram):
    from ensemble_cast import affect_for
    chars = dram.get("characters", [])
    top = sorted(chars, key=lambda c: -((c.get("mentions") or 0) +
                                        2 * (c.get("dialogue_lines") or 0)))[:5]
    names = [c.get("name", "") for c in top]
    vibes = vibe_of(slug, names)
    primary = vibes[0][0]
    # dialogue-heavy collections need a yielding narrator
    lines = sum(c.get("dialogue_lines") or 0 for c in chars)
    pace_note = ("dialogue-heavy: narrator must yield, frame not compete"
                 if lines > 40 else "narration-led: voice must carry alone")
    # scary + winter stack (kwaidan): cold tale, warm teller
    stack = [v for v, _ in vibes[:2]]
    np_ = _NARRATOR[primary]
    aff = affect_for(None, slug.replace("-", " ") + " " + " ".join(names))
    return {
        "collection": slug,
        "tradition": tradition_of(slug),
        "vibes": [{"vibe": v, "evidence": h[:3]} for v, h in vibes],
        "cast_notes": f"{len(chars)} figures, {lines} dialogue lines; " +
                      ", ".join(f"{c.get('name')}({c.get('dialogue_lines') or 0})"
                                for c in top[:4]),
        "narrator": {"voice": np_["voice"],
                     "why": np_["why"] + " " + pace_note + ".",
                     "affect": aff,
                     "sounds_like": sounds_like(aff.get("voice_words", []))},
    }


# smeared-name guard (handover open thread: "King"-style role names span
# books; Yes/The/Well are parsing artifacts). A real character recurs
# across few books; an entity in 6+ books with no role is a smeared role.
_JUNK_NAMES = {"yes", "the", "well", "and", "her", "him", "you", "sir",
               "god", "king", "man", "woman", "mother", "father",
               "alas", "ah", "oh", "ay"}


def _real_character(nm, apps, is_chair):
    if is_chair:
        return True
    if len(nm) < 3 or nm.lower() in _JUNK_NAMES:
        return False
    books = set(a[0] for a in apps)
    if len(books) > 5 and not any(a[1].get("role") for a in apps):
        return False
    return True


def character_thesis(name, appearances):
    """appearances: list of (book, char-record)."""
    from ensemble_cast import (brief_character, pitch_band, classify_archetype,
                               affect_for)
    total_m = sum(a[1].get("mentions") or 0 for a in appearances)
    total_l = sum(a[1].get("dialogue_lines") or 0 for a in appearances)
    books = sorted(set(a[0] for a in appearances))
    # richest record wins for traits; all samples kept
    best = max(appearances, key=lambda a: (a[1].get("dialogue_lines") or 0,
                                           a[1].get("mentions") or 0))[1]
    samples = [s for _, r in appearances
               for s in [(r.get("sample_line") or "").strip()] if s][:3]
    prof = {"name": name, "role": best.get("role"), "age": best.get("age"),
            "gender": best.get("gender"), "dialogue_lines": total_l}
    arch = classify_archetype(name, " ".join([best.get("role") or "",
                                             best.get("voice_query") or ""]))
    aff = affect_for(best.get("role"), name)
    why = (f"{total_m} mentions across {len(books)} book(s), {total_l} spoken lines" +
           (f"; speaks {best.get('dialogue_how', '')}" if best.get("dialogue_how") else "") +
           f". {brief_character(prof)}")
    return {
        "character": name, "books": books,
        "mentions": total_m, "dialogue_lines": total_l,
        "traits": {"gender": best.get("gender"), "age": best.get("age"),
                   "role": best.get("role")},
        "sample_lines": [s[:220] for s in samples],
        "predicted": {"archetype": arch.get("archetype"),
                      "delivery": (arch.get("profile") or {}).get("delivery", ""),
                      "pitch_hz": list(pitch_band(best.get("role"),
                                                 best.get("age"), best.get("gender"))),
                      "affect": aff,
                      "sounds_like": sounds_like(aff.get("voice_words", []))},
        "why": why,
    }


def ff_thesis():
    from channel_character import load_channel
    rec = load_channel("folk-and-fable")
    ddir = os.path.join(CHAN, "folk-and-fable", "dramatis")
    # per-collection narrator theses
    colls = []
    by_name: dict = {}
    for fp in sorted(glob.glob(os.path.join(ddir, "*.json"))):
        slug = os.path.basename(fp)[:-5]
        dram = _load(fp)
        if not dram:
            continue
        colls.append(collection_thesis(slug, dram))
        for c in dram.get("characters", []):
            nm = str(c.get("name", ""))
            if nm:
                by_name.setdefault(nm, []).append((slug, c))
    # characters: chairs pinned first, then top REAL speakers by dialogue
    chairs = list(((rec.get("voice") or {}).get("chairs") or {}).keys())
    chair_set = set(chairs)
    ranked = sorted(by_name.items(),
                    key=lambda kv: -sum((r.get("dialogue_lines") or 0)
                                        for _, r in kv[1]))
    chars = []
    lower_map = {k.lower(): k for k in by_name}
    for nm in chairs:
        key = lower_map.get(nm.lower())
        if key:
            chars.append(character_thesis(key, by_name[key]))
    for nm, apps in ranked:
        if nm.lower() in chair_set or len(chars) >= 10:
            continue
        if not _real_character(nm, apps, False):
            continue
        chars.append(character_thesis(nm, apps))
    return {"channel": "folk-and-fable",
            "narrator_model": "per-collection (Adrian demoted to candidate)",
            "collections": colls,
            "characters": chars}


def chair_thesis(slug, rec):
    from ensemble_cast import affect_for, classify_archetype
    out = []
    for name, c in ((rec.get("voice") or {}).get("chairs") or {}).items():
        direction = c.get("direction", "") or ""
        arch = classify_archetype(name, direction)
        aff = affect_for(None, name + " " + direction)
        locked = bool(c.get("fish_id"))
        out.append({
            "character": name,
            "status": ("locked: " + str(c.get("label", ""))) if locked else "open",
            "direction": direction[:200],
            "predicted": {"archetype": arch.get("archetype"),
                          "delivery": (arch.get("profile") or {}).get("delivery", ""),
                          "affect": aff,
                          "sounds_like": sounds_like(aff.get("voice_words", []))},
            "why": f"Channel pitch: {(rec.get('pitch', '') or '')[:160]} "
                   f"Chair brief: {direction[:160]}",
        })
    return {"channel": slug,
            "narrator_model": "single chair (no collections)",
            "pitch": (rec.get("pitch", "") or "")[:200],
            "characters": out}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    from channel_character import load_channel
    import sleep_studio as st
    slugs = [args.channel] if args.channel else \
        [c["slug"] for c in st.list_channels()]
    for slug in slugs:
        try:
            th = ff_thesis() if slug == "folk-and-fable" else \
                chair_thesis(slug, load_channel(slug))
            json.dump(th, open(os.path.join(OUT, slug + ".json"), "w"),
                      indent=1, ensure_ascii=False)
            n_c = len(th.get("collections", []))
            n_ch = len(th.get("characters", []))
            print(f"- {slug}: {n_c} collections, {n_ch} characters")
        except Exception as e:
            print(f"- {slug}: FAILED {e}"[:150])


if __name__ == "__main__":
    main()
