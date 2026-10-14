"""Character graph -> voice constraints. Not scoring tweaks: the graph
shrinks the possibility space BEFORE search (queries) and vetoes
contradictions (penalties).

Per (channel, character): all appearances, line terseness (sample-length
statistics as pace evidence), co-characters/relationships (who they share
books with, who talks most, pace contrast), story function, and from all
of it: search queries, anti-tag vetoes, gender lean, pace note.
"""
from __future__ import annotations

import glob
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS_DIR = os.path.normpath(os.path.join(_HERE, "..", "studio", "channels"))

# archetype -> vendor tags that CONTRADICT it (mismatch vetoes, -3 each).
# Small and principled: high-arousal tags on low-arousal types and vice
# versa. Absence of evidence is not evidence; presence of contradiction is.
ANTI_TAGS = {
    "elder": ("quick", "energetic", "cheerful", "dramatic", "playful",
              "animated", "excitable", "frantic"),
    "fae": ("deep", "harsh", "gravelly", "booming", "menacing", "dark"),
    "beast": ("squeaky", "giggly", "bubbly", "cute", "frantic"),
    "crone": ("bubbly", "giggly", "sweet", "cute", "perky"),
    "trickster": ("solemn", "grave", "ponderous", "funereal", "soporific"),
    "hero": ("menacing", "sinister", "creepy", "villainous"),
    "mentor": ("frantic", "giggly", "squeaky", "manic"),
    "innocent": ("menacing", "dark", "sinister", "gravelly", "sultry"),
    "overlord": ("giggly", "bubbly", "sweet", "perky", "meek"),
    "imp": ("solemn", "ponderous", "soporific", "grave"),
}


def build(channel_slug: str, chair: str) -> dict | None:
    """Aggregate every appearance + relationships + line evidence."""
    import sys as _sys
    base = os.path.normpath(os.path.join(_HERE, ".."))
    for _p in (base, os.path.join(base, "pipeline")):
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    from ensemble_cast import classify_archetype
    ddir = os.path.join(CHANNELS_DIR, channel_slug, "dramatis")
    if not os.path.isdir(ddir):
        return None
    want = chair.strip().lower()
    apps, others = [], []
    for fp in sorted(glob.glob(os.path.join(ddir, "*.json"))):
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        book = os.path.basename(fp)[:-5]
        mine = [c for c in d.get("characters", [])
                if want in str(c.get("name", "")).lower()]
        if not mine:
            continue
        apps.append((book, mine[0]))
        for c in d.get("characters", []):
            nm = str(c.get("name", ""))
            if nm and nm.lower() != mine[0].get("name", "").lower():
                others.append((book, nm, int(c.get("dialogue_lines") or 0),
                               int(c.get("mentions") or 0)))
    if not apps:
        return None
    rec = max((r for _, r in apps),
              key=lambda r: (int(r.get("dialogue_lines") or 0),
                             int(r.get("mentions") or 0)))
    # line terseness: mean sample length across appearances (pace evidence)
    samples = [(r.get("sample_line") or "").strip() for _, r in apps
               if (r.get("sample_line") or "").strip()]
    words = [len(s.split()) for s in samples]
    mean_len = round(sum(words) / len(words), 1) if words else 0
    terse = mean_len > 0 and mean_len <= 12
    # relationships: co-characters ranked by shared-book dialogue
    rel: dict = {}
    for book, nm, lines, mentions in others:
        e = rel.setdefault(nm, {"books": set(), "lines": 0, "mentions": 0})
        e["books"].add(book)
        e["lines"] += lines
        e["mentions"] += mentions
    rels = sorted(((nm, len(v["books"]), v["lines"], v["mentions"])
                   for nm, v in rel.items()),
                  key=lambda t: -(t[2] + t[3]))[:5]
    total_l = sum(int(r.get("dialogue_lines") or 0) for _, r in apps)
    arch = classify_archetype(rec.get("name", chair),
                              " ".join([str(rec.get("voice_query") or ""),
                                        str(rec.get("role") or "")]))
    arch_name = arch.get("archetype") if arch.get("confidence", 0) > 0 else ""
    # gender lean from evidence counts (soft: 69M/5F is decisive, 16M/35F isn't)
    g = {"gender": rec.get("gender"), "evidence": rec.get("gender_evidence", "")}
    # queries from the graph: species + trait words, not chair boilerplate
    species = [w for w in rec.get("name", chair).lower().split()
               if len(w) >= 4]
    queries = []
    if arch_name:
        try:
            from ensemble_cast import ARCHETYPES
            pace = ARCHETYPES[arch_name].get("pace", "")
            proj = ARCHETYPES[arch_name].get("projection", "")
            queries.append(" ".join([*species[:2], pace, proj,
                                     "narration"]).strip())
        except Exception:
            pass
    queries.append(" ".join([*species[:2], "narration"]).strip())
    pace_note = ("terse lines (avg %.0f words): slow, sparse, pausing delivery"
                 % mean_len) if terse else \
                ("flowing lines (avg %.0f words): carries longer passages"
                 % mean_len) if mean_len else "no line evidence"
    return {
        "ok": True, "name": rec.get("name", chair),
        "books": sorted(set(b for b, _ in apps)),
        "mentions": sum(int(r.get("mentions") or 0) for _, r in apps),
        "dialogue_lines": total_l,
        "gender": g, "age": rec.get("age"),
        "role": rec.get("role"),
        "samples": [s[:220] for s in samples[:4]],
        "mean_sample_words": mean_len,
        "pace_note": pace_note,
        "relationships": [{"with": nm, "shared_books": nb, "their_lines": ln,
                           "contrast": ("talks more — yield to them" if ln > total_l
                                        else "you carry — they color around you")}
                          for nm, nb, ln, _ in rels],
        "archetype": arch_name,
        "vetoes": list(ANTI_TAGS.get(arch_name, ())),
        "queries": [q for q in queries if q],
    }
