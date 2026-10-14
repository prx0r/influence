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

# drafted briefs for chairs with empty directions (DRAFT status in sheet
# only — never written to channel records until the owner promotes them).
DRAFT_BRIEFS = {
    ("corbin-sleep", "guest"): "quiet guest voice, first-time wonder, unhurried",
    ("longhaul-journeys", "crew"): "warm crew voice, cabin-calm, unhurried",
    ("longhaul-journeys", "ground"): "calm tower voice, precise and measured",
}


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
            draft = DRAFT_BRIEFS.get((slug, name), "")
            r = ob.propose(slug, name, 5, direction=draft)
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
            "brief_draft": draft or "",
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
    # joint pass: one voice can't headline two channels. First claim wins;
    # later chairs with the same #1 fall through to their best unclaimed
    # alternative (narrator chairs may share the house bed voice — flagged,
    # not forced; character chairs must differ).
    import channel_onboard as ob
    taken: dict = {}
    results = {}
    for slug in slugs:
        try:
            results[slug] = (assign_channel(slug), ob)
        except Exception as e:
            print(f"- {slug}: FAILED {e}"[:150])
    for slug, (a, _) in results.items():
        changed = 0
        for x in a["assignments"]:
            if x.get("status") != "recommended":
                continue
            rec = x.get("recommended", {})
            vid = rec.get("voice_id", "")
            is_narrator = x["chair"].strip().lower() in {
                "narrator", "monk", "lecturer", "anchor", "loremaster",
                "guide", "companion", "documentarian", "clinician",
                "foreman", "imaginal", "guest", "crew", "ground", "mommy"}
            if vid and vid in taken and taken[vid] != (slug, x["chair"]):
                if is_narrator:
                    x["note"] = f"shares house voice with {taken[vid][0]}"
                    continue
                alt = next((c for c in x.get("alternatives", [])
                            if c.get("voice_id") not in taken), None)
                if alt:
                    altrecs = [c for c in [alt] + x.get("alternatives", [])
                               if c.get("voice_id") != vid]
                    x["alternatives"] = (
                        [{"voice_id": vid, "name": rec.get("name"),
                          "score": rec.get("score"), "note": "taken by " +
                           taken[vid][0]}] + altrecs)
                    x["recommended"] = {
                        "voice_id": alt.get("voice_id", ""),
                        "name": alt.get("name", ""),
                        "score": alt.get("score"),
                        "why": "best unclaimed (house collision resolved)"}
                    changed += 1
            if vid:
                taken.setdefault(x["recommended"].get("voice_id", ""), (slug, x["chair"]))
        json.dump(a, open(os.path.join(OUT, slug + ".json"), "w"),
                  indent=1, ensure_ascii=False)
        recn = sum(1 for x in a["assignments"]
                   if x.get("status") == "recommended")
        lok = sum(1 for x in a["assignments"]
                  if x.get("status") == "locked")
        print(f"- {slug}: {recn} recommended, {lok} locked" +
              (f" ({changed} collisions resolved)" if changed else ""))


if __name__ == "__main__":
    main()
