#!/usr/bin/env python3
"""Verbatim readout readiness: easy source -> clean body + report.

For each folk-and-fable collection: extract PG body (START..END markers),
drop license header, flag truncation (no END marker / ends mid-sentence),
junk-scan, prep-score a head sample. Writes
studio/readiness-folk-and-fable.json. No audio rendered here.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, "/root/influence")
sys.path.insert(0, "/root/influence/pipeline")
from pipeline import tts_text as t

JUNK = {
    "urls": re.compile(r"https?://|www\."),
    "footnotes": re.compile(r"\[[0-9]+\]"),
    "transcriber": re.compile(r"Transcriber", re.I),
    "contents_dots": re.compile(r"\.{4,}"),
    "page_nums": re.compile(r"\[?Pg \d+\]?", re.I),
}


def extract(src):
    raw = open(src, encoding="utf-8", errors="replace").read()
    i = raw.find("*** START OF")
    body = raw[raw.find("\n", i) + 1:] if i >= 0 else raw
    j = body.find("*** END OF")
    complete = True
    if j >= 0:
        body = body[:j]
    else:
        tail = body.rstrip()[-120:]
        if not re.search(r"[.!?\"”]$", body.rstrip()):
            complete = False
    words = body.split()
    return body, words, complete


def main():
    out = {"collections": []}
    for d in sorted(glob.glob("/root/easy/folk-and-fable/*/")):
        slug = os.path.basename(d.rstrip("/"))
        src = os.path.join(d, "source.txt")
        if not os.path.exists(src):
            continue
        body, words, complete = extract(src)
        sample = " ".join(words[:1500])
        sc = t.score(sample)
        junk = {k: len(p.findall(body)) for k, p in JUNK.items()}
        out["collections"].append({
            "collection": slug,
            "words": len(words),
            "est_min": round(len(words) / 150),
            "complete": complete,
            "score_head": sc["score"],
            "junk": {k: v for k, v in junk.items() if v},
            "readout_staged": bool(glob.glob(
                f"/root/damn/projects/folk-and-fable/readout/*.read.txt")),
        })
    json.dump(out, open(
        "/root/influence/studio/readiness-folk-and-fable.json", "w"), indent=1)
    renderable = [c for c in out["collections"]
                  if c["complete"] and not c["junk"]]
    print(f"{len(out['collections'])} collections, "
          f"{sum(c['words'] for c in out['collections'])} words total, "
          f"~{sum(c['est_min'] for c in out['collections'])} min total")
    print(f"clean+complete: {len(renderable)}")
    for c in out["collections"]:
        flag = "" if (c["complete"] and not c["junk"]) else "  <-- NEEDS WORK"
        print(f"{c['collection'][:32]:32} {c['words']:>6}w ~{c['est_min']:>4}min "
              f"score={c['score_head']:<3} complete={c['complete']} junk={c['junk']}{flag}")


if __name__ == "__main__":
    main()
