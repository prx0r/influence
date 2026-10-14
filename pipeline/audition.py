#!/usr/bin/env python3
"""Objective audition protocol — THE process for every character.

Same passage (the character's own lines from the graph), same speed
(from the archetype pace target), every contender, $0 free tier.
Takes land in the voice bank, get measured against the predicted band,
and the sheet records take-fit (judge takes, not vendor samples).

Usage: python3 pipeline/audition.py folk-and-fable Tortoise [n=3]
"""
import sys

_HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
sys.path.insert(0, __import__("os").path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/root/influence/dash")


def run_audition(channel: str, character: str, n: int = 3,
                 speed: float = 0.8) -> dict:
    import channel_onboard as ob
    import sleep_studio as st
    from character_graph import build as _build
    from character_engine import derive_band, fit_score, PACE_TARGET
    from voice_listen import listen as _listen
    import glob as _gg

    g = _build(channel, character)
    if not g:
        return {"ok": False, "reason": f"no graph for {character}"}
    # passage = the character's own longest sample lines (their words)
    lines = sorted(set(g["samples"]), key=len, reverse=True)[:3]
    passage = " ".join(lines)[:400] or f"I am {character}."
    band = derive_band(channel, character)
    arch = band.get("archetype", "")
    # fixed speed from archetype pace target (slow lane; sleep never hurries)
    tgt = PACE_TARGET.get(arch, 2.2)
    spd = round(max(0.5, min(1.0, speed if speed else tgt / 2.6)), 2)
    r = ob.propose(channel, character, max(n + 2, 5),
                   direction=" ".join(g["queries"][:1]))
    if not r.get("ok"):
        return {"ok": False, "reason": r.get("reason", "propose failed")}
    takes = []
    for c in r["candidates"][:n]:
        ren = st.free_narrate(passage, c["voice_id"], speed=spd)
        if not ren.get("ok"):
            takes.append({"voice": c["name"], "ok": False,
                          "reason": ren.get("reason", "")})
            continue
        f = _gg.glob(f"/root/sleepdraw/runs/studio/voice/{ren['name']}")
        m, fit = {}, {}
        if f:
            try:
                m = _listen(f[0])
                fit = fit_score(m, {**band["band"],
                                    "f0std_hz": [0, 60],
                                    "flatness": "mid"})
            except Exception as e:
                fit = {"fit": None, "notes": [str(e)[:100]]}
        takes.append({"voice": c["name"], "voice_id": c["voice_id"],
                      "clip": ren["name"], "url": ren["url"],
                      "take_f0": (m or {}).get("f0_median_hz"),
                      "take_rate": (m or {}).get("syllables_per_sec"),
                      "take_fit": fit.get("fit"), "tag_score": c["score"]})
    takes.sort(key=lambda t: -(t["take_fit"] if t["take_fit"] is not None
                               else t["tag_score"]))
    return {"ok": True, "character": character, "archetype": arch,
            "passage": passage, "speed": spd, "takes": takes,
            "rule": "same words, same speed, measured takes decide"}


def main():
    import json
    a = sys.argv[1:]
    channel = a[0] if len(a) > 0 else "folk-and-fable"
    character = a[1] if len(a) > 1 else "Tortoise"
    n = int(a[2]) if len(a) > 2 else 3
    print(json.dumps(run_audition(channel, character, n), indent=1))


if __name__ == "__main__":
    main()
