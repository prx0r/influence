"""Cast extraction — scan a book, identify characters, profile them,
suggest voices. Stdlib only, $0, offline.

Pipeline: names (proper-noun frequency, sentence-start filtered) →
dialogue attribution (speech verbs both directions) → gender/age/role
cues (pronoun windows, title lexicon) → voice query per character.
Nothing guessed silently: every hint carries its evidence; low-evidence
fields stay null for human/pi review.
"""
from __future__ import annotations

import re
from collections import Counter

_SPEECH_VERBS = ("said|cried|asked|replied|whispered|shouted|answered|"
                 "continued|exclaimed|murmured|called|returned|added|"
                 "observed|remarked|sighed|laughed|groaned")
_QUOTE_PAT = re.compile(
    r"[“\"]([^”\"]{5,400}?)[”\"]\s*,?\s*(?:" + _SPEECH_VERBS + r")\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)")
_QUOTE_PAT_REV = re.compile(
    r"([A-Z][A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:" + _SPEECH_VERBS + r")\s*[:,]?\s*[“\"]")
_NAME_PAT = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b")
_SENT_END = re.compile(r"(?<=[.!?])\s+")

_STOP_NAMES = {"The", "And", "But", "For", "With", "From", "That", "This",
              "When", "Where", "Which", "There", "They", "What", "You",
              "Your", "His", "Her", "Its", "Our", "Their", "Project",
              "Gutenberg", "Chapter", "Part", "Book", "Tale", "Story",
              "Once", "Then", "Now", "Here", "Thus", "However", "After",
              "Before", "While", "Because", "Although", "Though", "Upon",
              "Between", "Among", "Within", "Without", "Through", "During",
              "Kingdom", " Palace", "Evening", "Morning", "Night", "Day"}

_MALE = {"he", "him", "his", "himself", "king", "prince", "emperor", "man",
         "boy", "lad", "husband", "father", "son", "brother", "uncle",
         "grandfather", "wizard", "giant", "woodcutter", "fisherman",
         "soldier", "merchant", "ferryman", "boatman"}
_FEMALE = {"she", "her", "hers", "herself", "queen", "princess", "empress",
           "woman", "girl", "lass", "wife", "mother", "daughter", "sister",
           "aunt", "grandmother", "witch", "fairy", "maiden", "bride", "wife"}
_YOUNG = {"boy", "girl", "lad", "lass", "child", "young", "little",
          "apprentice", "son", "daughter", "prince", "princess", "baby"}
_OLD = {"old", "elder", "aged", "grandmother", "grandfather", "ancient",
        "grey", "gray", "wrinkled"}
_ROLES = ["king", "queen", "prince", "princess", "emperor", "witch",
          "wizard", "giant", "dwarf", "fairy", "woodcutter", "fisherman",
          "soldier", "merchant", "ferryman", "maiden", "bride", "mother",
          "father", "captain", "sailor", "hunter", "shepherd", "miller",
          "tailor", "shoemaker", "baker", "smith"]


def _names(text: str, min_freq: int = 3) -> Counter:
    """Proper-noun candidates: capitalized, not sentence-initial, not stop."""
    counts: Counter = Counter()
    for sent in _SENT_END.split(text):
        for m in _NAME_PAT.finditer(sent):
            name = m.group(1)
            if m.start() == 0:
                continue  # sentence start — not evidence
            # strip leading articles/titles ("The Tree" → Tree)
            parts = name.split()
            while parts and parts[0] in _STOP_NAMES:
                parts.pop(0)
            if not parts:
                continue
            name = " ".join(parts)
            first = name.split()[0]
            if first in _STOP_NAMES or name in _STOP_NAMES:
                continue
            counts[name] += 1
    # common nouns wearing capitals mid-sentence (Tree/tree, Shoes/shoes):
    # drop names whose LOWERCASE-only occurrences rival the capitalized
    # ones (a true name is almost never written lowercase).
    lower_counts = Counter(re.findall(r"[a-z]{3,}", text.lower()))
    kept = {}
    for name, v in counts.items():
        if v < min_freq:
            continue
        twin = lower_counts.get(name.lower(), 0) - v
        if twin > v and len(name.split()) == 1:
            continue  # "Tree" with 40x lowercase "tree" is furniture
        kept[name] = v
    return Counter(kept)


def _dialogue(text: str) -> dict[str, list[str]]:
    """speaker → quoted lines (both attribution directions)."""
    out: dict[str, list[str]] = {}
    for m in _QUOTE_PAT.finditer(text):
        out.setdefault(m.group(2).split()[-1], []).append(m.group(1).strip())
    for m in _QUOTE_PAT_REV.finditer(text):
        out.setdefault(m.group(1).split()[-1], []).append("")
    return out


def _proximity_dialogue(text: str, names: list[str],
                        radius: int = 400) -> dict[str, list[str]]:
    """Fallback for literary attribution (pronouns/context instead of
    'said X'): each quote goes to the nearest preceding named character.
    Evidence is weaker — flagged as proximity, not proof."""
    out: dict[str, list[str]] = {}
    quotes = [(m.start(), m.group(0)[:200])
              for m in re.finditer(r"[“\"]([^”\"]{5,400}?)[”\"]", text)]
    if not quotes:
        return out
    spots: list[tuple[int, str]] = []
    for name in names:
        for m in re.finditer(r"\b" + re.escape(name) + r"\b", text):
            spots.append((m.start(), name))
    spots.sort()
    import bisect
    starts = [s[0] for s in spots]
    for qpos, qtext in quotes:
        i = bisect.bisect_right(starts, qpos) - 1
        if i < 0:
            continue
        spos, sname = spots[i]
        if qpos - spos <= radius:
            out.setdefault(sname, []).append(qtext)
    return out


def _window_cues(text: str, name: str, radius: int = 150) -> Counter:
    """Gender/age/role cue words near any mention of the name."""
    cues: Counter = Counter()
    low = text.lower()
    for m in re.finditer(re.escape(name.lower()), low):
        win = low[max(0, m.start() - radius):m.end() + radius]
        for w in set(re.findall(r"[a-z]+", win)):
            if w in _MALE or w in _FEMALE or w in _YOUNG or w in _OLD:
                cues[w] += 1
    return cues


def _gender(cues: Counter) -> tuple[str | None, str]:
    m = sum(v for k, v in cues.items() if k in _MALE)
    f = sum(v for k, v in cues.items() if k in _FEMALE)
    if m + f < 2:
        return None, "too little evidence"
    if m >= 2 * f:
        return "male", f"{m}M/{f}F cues"
    if f >= 2 * m:
        return "female", f"{m}M/{f}F cues"
    return None, f"contested {m}M/{f}F"


def _age(cues: Counter) -> tuple[str | None, str]:
    y = sum(v for k, v in cues.items() if k in _YOUNG)
    o = sum(v for k, v in cues.items() if k in _OLD)
    if y + o < 1:
        return None, "no age cues"
    if y > o:
        return "young", f"{y}y/{o}o"
    if o > y:
        return "old", f"{y}y/{o}o"
    return None, f"tied {y}y/{o}o"


def _role(name: str, cues: Counter, text: str,
          shared_roles: set | None = None) -> tuple[str | None, str]:
    low = name.lower()
    for r in _ROLES:
        if re.search(r"\b" + r + r"\b", low):
            return r, "in name"
    scored = [(cues.get(r, 0), r) for r in _ROLES]
    scored.sort(reverse=True)
    if scored and scored[0][0] >= 2 and scored[0][1] not in (shared_roles or set()):
        return scored[0][1], f"{scored[0][0]} nearby mentions"
    if scored and scored[0][0] >= 2:
        return None, f"contested role ({scored[0][1]} shared across cast)"
    return None, "no role cues"


def dramatis(text: str, min_freq: int = 3) -> list[dict]:
    """Full character extraction → profiles with evidence + voice query."""
    names = _names(text, min_freq)
    dlg = _dialogue(text)
    # fold surnames/titles to last token ("Old Mosaku" → Mosaku)
    folded: dict[str, dict] = {}
    for name, freq in names.items():
        key = name.split()[-1]
        f = folded.setdefault(key, {"names": set(), "freq": 0})
        f["names"].add(name)
        f["freq"] += freq
    out = []
    # shared role words (setting vocabulary, not identity): claimed by 3+
    all_cues = {key: _window_cues(text, key) for key in folded}
    role_claims: dict[str, int] = {}
    for key, cues in all_cues.items():
        for r in _ROLES:
            if cues.get(r, 0) >= 2:
                role_claims[r] = role_claims.get(r, 0) + 1
    shared = {r for r, n in role_claims.items() if n >= 3}
    prox = _proximity_dialogue(text, list(folded.keys()))
    for key, f in sorted(folded.items(), key=lambda kv: -kv[1]["freq"]):
        cues = all_cues[key]
        gender, g_ev = _gender(cues)
        age, a_ev = _age(cues)
        role, r_ev = _role(key, cues, text, shared)
        lines = dlg.get(key, [])
        if not lines and key in prox:
            lines = prox[key]
            how = "proximity"
        else:
            how = "attributed" if lines else "none"
        q = " ".join(x for x in [age or "", gender or "", role or "",
                                 "narration"] if x)
        out.append({"name": key, "aliases": sorted(f["names"]),
                    "mentions": f["freq"], "dialogue_lines": len(lines),
                    "gender": gender, "gender_evidence": g_ev,
                    "age": age, "age_evidence": a_ev,
                    "role": role, "role_evidence": r_ev,
                    "voice_query": q or "calm narration",
                    "sample_line": (lines[0][:160] if lines else ""),
                    "dialogue_how": how})
    return out


def cast_book(path: str, min_freq: int = 3) -> dict:
    """One book file → dramatis + voice queries. Pure, offline."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    chars = dramatis(text, min_freq)
    return {"source": path, "characters": chars,
            "n_characters": len(chars),
            "speaking": sum(1 for c in chars if c["dialogue_lines"] > 0)}
