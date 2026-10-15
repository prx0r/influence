#!/usr/bin/env python3
"""ttslop — TTS/character quality classifier (Jev-style, deterministic, $0).

Grades a damn drama/readout file the way noslop grades prose: verdict +
calibrated-feeling score + per-line matches with why + fix. Four dimensions:

  READINESS    prep score, damn gate + poison per chunk, chunk budget
  DIRECTION    stage-direction coverage + tag vocabulary (drama files)
  ATTRIBUTION  quoted speech explicitly voiced by character chairs vs
               narrator-read (named verbs = proof, pronouns = narrator keeps)
  HICCUPS      leftover digits/URLs/brackets/acronyms/romans/doubles/non-ascii

Usage: ttslop.py <file.drama.txt|file.read.txt> [--channel slug] [--json]
Verdict: READY / NEEDS_WORK / BLOCKED. Pure stdlib, no network.
Human verdicts append to studio/ttslop-verdicts.jsonl for future calibration.
"""
import json
import os
import re
import sys

sys.path.insert(0, "/root/influence")
sys.path.insert(0, "/root/influence/pipeline")
sys.path.insert(0, "/root/damn/fish")
sys.path.insert(0, "/root/influence/dash")

from pipeline import tts_text as t
from gate import gate

KNOWN_TAGS = {
    "[whispering]", "[pause]", "[soft pause]", "[long pause]", "[slow]",
    "[quieter, closer]", "[slowly]", "[gently]", "[softly]",
    "[calm, measured storyteller voice, slow and gentle for sleep]",
}
# benign non-ascii: Fish pronounces these natively (proven in shipped masters)
BENIGN_NONASCII = set("’‘“”–—…àáâäæçéèêëíîïñóôöøúûüýÿœßÆŒ")


def _tag_known(tag):
    if tag in KNOWN_TAGS or tag.startswith("[pause"):
        return True
    if tag.startswith("<|speaker:"):  # structural, not direction
        return True
    if "," in tag:  # qualified beats: [gentle, barely a breath between]
        return True
    return False
HICCUP_PATS = [
    ("url", re.compile(r"https?://|www\."), "strip source link"),
    ("footnote", re.compile(r"\[[0-9]+\]"), "already stripped? check"),
    ("allcaps-line", re.compile(r"^[A-Z][A-Z \-\,\;]{15,}$", re.M),
     "frontmatter not stripped"),
    ("underscore", re.compile(r"_"), "italics markup — strip"),
    ("asterisks", re.compile(r"\*{3,}"), "scene break → [long pause]"),
    ("single-roman", re.compile(r"\b(Part|Chapter|Book) [IVX]\b"),
     "reads as letter — expand to cardinal"),
    ("currency", re.compile(r"[$£€]"), "expand to words"),
    ("non-ascii", re.compile(r"[^\x00-\x7F]"), "verify Fish pronounces"),
    ("double-word", re.compile(r"\b(\w+) \1\b", re.I), "likely typo — fix word"),
    (" Mr/Mrs/St ", re.compile(r"\b(Mr|Mrs|Ms|St|Dr|Jr|Sr)\."), "expand title"),
]
QUOTE_RE = re.compile(r"[“\"]([^”\"]{3,300}?)[”\"]")
SAID_RE = re.compile(
    r"\b(said|cried|asked|replied|whispered|shouted|answered|murmured|"
    r"sighed|called|told)\b\s+([A-Z][a-z]+)|\b([A-Z][a-z]+)\s+"
    r"(said|cried|asked|replied|whispered|shouted|answered|murmured|"
    r"sighed|called)\b")


def grade_direction(text, is_drama):
    tags = re.findall(r"\[[a-z][a-z \-',]*\]|<[^>\n]{1,40}>", text)
    if not is_drama:
        return {"score": 100, "coverage": None,
                "note": "readout: performance carried by casting, no tags expected",
                "unknown_tags": []}
    segs = [s for s in re.split(r"<\|speaker:\d+\|>", text) if s.strip()]
    tagged = sum(1 for s in segs
                 if re.search(r"\[[a-z][a-z \-',]*\]", s))
    unknown = sorted({g for g in tags if not _tag_known(g)})
    cov = tagged / max(1, len(segs))
    score = round(100 * (0.5 + 0.5 * cov)) - min(20, 5 * len(unknown))
    return {"score": max(0, score),
            "coverage": f"{tagged}/{len(segs)} segments tagged",
            "unknown_tags": unknown,
            "note": "unknown tags still render (Fish reads through) — add to KNOWN_TAGS or fix"}


def grade_attribution(text):
    quotes = list(QUOTE_RE.finditer(text))
    if not quotes:
        return {"score": 100, "coverage": "no quoted speech",
                "voiced": 0, "narrator_read": 0, "samples": []}
    voiced, samples = 0, []
    for m in quotes:
        window = text[max(0, m.start() - 120):m.end() + 120]
        sm = SAID_RE.search(window)
        if sm:
            voiced += 1
            who = sm.group(2) or sm.group(3)
            if len(samples) < 5:
                samples.append(f"{who}: “{m.group(1)[:60]}…”")
    total = len(quotes)
    cov = voiced / total
    score = round(100 * cov) if total else 100
    return {"score": score,
            "coverage": f"{voiced}/{total} quotes name-attributed",
            "voiced": voiced, "narrator_read": total - voiced,
            "samples": samples,
            "note": "pronoun-only quotes stay narrator-voiced by design "
                    "(misattribution is worse)"}


def grade_hiccups(text):
    matches = []
    lines = text.splitlines()
    for name, pat, fix in HICCUP_PATS:
        for i, ln in enumerate(lines):
            if ln.startswith("//"):
                continue  # production comments never render (parse strips)
            if name == "non-ascii" and not (
                    set(ln) - set(ln.encode("ascii", "ignore").decode())
                    - BENIGN_NONASCII):
                continue
            if pat.search(ln):
                matches.append({"line": i + 1, "tag": name,
                                "text": ln.strip()[:100], "fix": fix})
                if len(matches) >= 25:
                    break
        if len(matches) >= 25:
            break
    score = max(0, 100 - 8 * len(matches))
    return {"score": score, "hits": len(matches), "matches": matches}


def grade(path, channel=None):
    txt = open(path, encoding="utf-8", errors="replace").read()
    is_drama = path.endswith(".drama.txt")
    # grade what renders: parse_drama strips // production comments
    body = "\n".join(l for l in txt.splitlines()
                     if not l.startswith("//")).strip()
    prepped = t.prep(body)
    score = t.score(body)["score"]
    chunks = prepped.get("chunks", [])
    gpass, gblocks = True, []
    for i, c in enumerate(chunks):
        g = gate(c)
        if not g.get("pass"):
            gpass = False
            gblocks.extend(f"chunk{i}: {b}" for b in g.get("blocks", [])[:2])
        if len(gblocks) > 6:
            break
    over = sum(1 for c in chunks if len(c.encode()) > 15000)
    readiness = max(0, score - (40 if not gpass else 0) - (30 if over else 0)
                    - (30 if not chunks else 0))
    direction = grade_direction(txt if is_drama else body, is_drama)
    attribution = grade_attribution(body)
    if not is_drama:
        # verbatim readout: single narrator carries all dialogue by design.
        # Attribution is excused (not scored); its weight redistributes.
        attribution = {"score": None, "coverage": "narrator carries all",
                       "voiced": 0, "narrator_read": 0, "samples": [],
                       "note": "readout has no speaker architecture by design"}
    hiccups = grade_hiccups(body)
    wsum = {"readiness": 0.35, "direction": 0.25, "attribution": 0.20,
            "hiccups": 0.20}
    parts = {"readiness": readiness, "direction": direction["score"],
             "attribution": attribution["score"], "hiccups": hiccups["score"]}
    scored = {k: v for k, v in parts.items() if v is not None}
    w = sum(wsum[k] for k in scored)
    total = round(sum(scored[k] * wsum[k] for k in scored) / w)
    if not gpass or over or not chunks:
        verdict = "BLOCKED"
    elif total >= 75 and score >= 70:
        verdict = "READY"
    else:
        verdict = "NEEDS_WORK"
    return {"file": path, "verdict": verdict, "score": total,
            "parts": parts, "chunks": len(chunks),
            "direction": direction, "attribution": attribution,
            "hiccups": hiccups, "gate_blocks": gblocks[:6]}


def main():
    path = sys.argv[1]
    as_json = "--json" in sys.argv
    rep = grade(path)
    if as_json:
        print(json.dumps(rep, indent=1))
        return
    print(f"{rep['file']}\n  {rep['verdict']} {rep['score']}  "
          f"{rep['parts']}  chunks={rep['chunks']}")
    if rep["gate_blocks"]:
        print("  GATE:", rep["gate_blocks"][:4])
    d = rep["direction"]
    print(f"  DIRECTION {d['score']}: {d.get('coverage')} {d.get('note','')}")
    if d.get("unknown_tags"):
        print("   unknown:", d["unknown_tags"][:6])
    a = rep["attribution"]
    print(f"  ATTRIBUTION {a['score']}: {a['coverage']}")
    for s in a.get("samples", [])[:5]:
        print("   e.g.", s)
    h = rep["hiccups"]
    print(f"  HICCUPS {h['score']}: {h['hits']} hits")
    for m in h["matches"][:10]:
        print(f"   L{m['line']} [{m['tag']}] {m['text'][:70]} → {m['fix']}")
    if rep["verdict"] == "READY":
        print("  → render free: render_pilot(path, channel_slug, speed=1.0)")


if __name__ == "__main__":
    main()
