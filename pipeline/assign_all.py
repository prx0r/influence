#!/usr/bin/env python3
"""Batch voice assignment for every channel (autonomous, $0 reads only).

For each channel x chair: propose top-5 via the engine, record the
recommendation + why + alternatives. NEVER locks (locks need a human
reason — binding law). Output: studio/casting/<slug>.json

Usage: python3 pipeline/assign_all.py [--channel slug]
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/root/influence/dash")

OUT = "/root/influence/studio/casting"


def assign_channel(slug: str) -> dict:
    import channel_onboard as ob
    from channel_character import load_channel
    rec = load_channel(slug)
    chairs = (rec.get("voice") or {}).get("chairs", {})
    out = {"channel": slug,
           "display_name": rec.get("display_name", slug),
           "pitch": (rec.get("pitch", "") or "")[:200],
           "assignments": []}
    for name, c in chairs.items():
        if not isinstance(c, dict):
            continue
        if c.get("fish_id"):
            out["assignments"].append({
                "chair": name, "status": "locked",
                "voice_id": c.get("fish_id"),
                "label": c.get("label", "")})
            continue
        try:
            r = ob.propose(slug, name, 5)
        except Exception as e:
            out["assignments"].append({"chair": name, "status": "error",
                                       "reason": str(e)[:120]})
            continue
        if not r.get("ok"):
            out["assignments"].append({"chair": name, "status": "error",
                                       "reason": r.get("reason", "")})
            continue
        cands = r.get("candidates", [])
        top = cands[0] if cands else {}
        out["assignments"].append({
            "chair": name, "status": "recommended",
            "direction": (c.get("direction", "") or "")[:200],
            "archetype": (r.get("archetype") or {}).get("name"),
            "coherence": r.get("coherence"),
            "recommended": {"voice_id": top.get("voice_id", ""),
                            "name": top.get("name", ""),
                            "score": top.get("score"),
                            "why": (top.get("reason", "") or "")[:300]},
            "alternatives": [{"voice_id": x.get("voice_id", ""),
                              "name": x.get("name", ""),
                              "score": x.get("score")} for x in cands[1:]],
            "audition": f"/audition.html?m=auditions/{slug}-{name}.json "
                        f"(render on request)"})
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    import sleep_studio as st
    slugs = [args.channel] if args.channel else \
        [c["slug"] for c in st.list_channels()]
    for slug in slugs:
        try:
            a = assign_channel(slug)
            json.dump(a, open(os.path.join(OUT, slug + ".json"), "w"),
                      indent=1, ensure_ascii=False)
            rec = sum(1 for x in a["assignments"]
                      if x.get("status") == "recommended")
            lok = sum(1 for x in a["assignments"]
                      if x.get("status") == "locked")
            print(f"- {slug}: {rec} recommended, {lok} locked")
        except Exception as e:
            print(f"- {slug}: FAILED {e}"[:150])


if __name__ == "__main__":
    main()
