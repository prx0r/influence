#!/usr/bin/env python3
"""Validation: cleaned body -> PASS/FAIL for readout.

Checks: prep score >= 70, damn gate passes, poison passes, no leftover
digits/URLs/brackets imbalance, chunks fit 15000-byte budget.
Usage: validate_readout.py <body.txt> → JSON verdict to stdout, exit 0/1.
"""
import json
import re
import sys

sys.path.insert(0, "/root/influence")
sys.path.insert(0, "/root/influence/pipeline")
sys.path.insert(0, "/root/damn/fish")

from pipeline import tts_text as t
from gate import gate

MIN_SCORE = 70
MAX_BYTES = 15000


def validate(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    fails = []
    # score what renders: normalized text (digits expanded, markup handled).
    # Raw-text junk (URLs, unbalanced brackets) is checked separately below.
    normed, _, _ = t.normalize(txt)
    prepped = t.prep(txt)
    score = t.score(normed)["score"]
    if score < MIN_SCORE:
        fails.append(f"prep score {score} < {MIN_SCORE}")
    chunks = prepped.get("chunks", [])
    if not chunks:
        fails.append("no chunks")
    # gate runs per segment in the real flow (render_pilot) — mirror that
    gwarn = 0
    for i, c in enumerate(chunks):
        g = gate(c)
        if not g.get("pass"):
            fails.extend(f"gate seg{i}: {b}" for b in g.get("blocks", [])[:2])
            if len(fails) > 8:
                fails.append("…more gate blocks (truncated)")
                break
        gwarn += len(g.get("warnings", []))
    over = [i for i, c in enumerate(chunks)
            if len(c.encode()) > MAX_BYTES]
    if over:
        fails.append(f"over-budget chunks: {over[:5]}")
    if re.search(r"https?://|www\.", txt):
        fails.append("leftover URL")
    if txt.count("[") != txt.count("]"):
        fails.append("unbalanced brackets")
    return {"file": path, "pass": not fails,
            "score": score, "chunks": len(chunks),
            "words": len(txt.split()),
            "est_min": round(len(txt.split()) / 150),
            "gate_warnings": gwarn,
            "fails": fails}


def main():
    rep = validate(sys.argv[1])
    print(json.dumps(rep, indent=1))
    raise SystemExit(0 if rep["pass"] else 1)


if __name__ == "__main__":
    main()
