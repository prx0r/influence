"""Data-driven character engine: character profile -> voice, derived.

Pipeline (every step reads the previous step's output, nothing hand-set):
  graph (lines, relationships, pace evidence)
    -> theory (bioacoustics: size->pitch/formants, motivation->texture,
       arousal->tempo + archetype delivery/tags/vetoes)
    -> search (theory queries -> Fish catalogue, free reads)
    -> listen (measure samples: F0, formants, rate, pauses)
    -> fit (distance-to-band -> slate + coherence + measured reasons)
    -> render (character tempo -> prosody.speed on s2.1-pro-free, $0)
    -> learn (ranks -> pairs -> BT; separate loop, same shapes)

Usage: python3 pipeline/character_engine.py folk-and-fable Tortoise
"""
from __future__ import annotations

import json
import sys

_HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
sys.path.insert(0, __import__("os").path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/root/influence/dash")

# archetype -> target syllable rate (sleep lane; comedy lane runs hotter).
# Grounded: sleep narration 135-170wpm ~= 2.0-2.6 syl/s at our measurement.
PACE_TARGET = {"elder": 1.8, "crone": 2.0, "mentor": 2.0, "beast": 1.8,
               "overlord": 1.9, "fae": 2.3, "hero": 2.4, "innocent": 2.5,
               "trickster": 2.8, "imp": 2.9}
# archetype -> texture targets (motivation axis, Morton MS rules).
# f0std: deadpan menace is FLAT (beast/overlord), play is VARIED (trickster).
# flatness: hostile/dominant is harsh/broadband (high), appeasing is tonal.
TEXTURE_TARGET = {
    "beast": {"f0std": (0, 12), "flatness": "high"},
    "overlord": {"f0std": (0, 12), "flatness": "high"},
    "elder": {"f0std": (0, 20), "flatness": "mid"},
    "crone": {"f0std": (5, 25), "flatness": "mid"},
    "mentor": {"f0std": (5, 20), "flatness": "low"},
    "hero": {"f0std": (10, 35), "flatness": "low"},
    "fae": {"f0std": (10, 40), "flatness": "low"},
    "innocent": {"f0std": (10, 35), "flatness": "low"},
    "trickster": {"f0std": (15, 60), "flatness": "mid"},
    "imp": {"f0std": (15, 60), "flatness": "mid"},
}

# archetype -> want LOW dispersion (big) or HIGH (small). Formants are the
# honest size cue (Fitch): big types minimize, small types maximize.
DISP_WANT_LOW = {"elder", "beast", "overlord", "crone", "mentor"}


def derive_band(channel: str, name: str) -> dict:
    """Graph + theory -> predicted acoustic band. The derivation is the product."""
    from character_graph import build as _build
    from ensemble_cast import ARCHETYPES, ARCHETYPE_TAGS
    g = _build(channel, name)
    if not g:
        return {"ok": False, "reason": f"no graph for {name}"}
    arch = g.get("archetype", "")
    prof = ARCHETYPES.get(arch, {})
    pitch = prof.get("pitch", (100, 160))
    tex = TEXTURE_TARGET.get(arch, {"f0std": (5, 40), "flatness": "mid"})
    return {
        "ok": True, "character": g["name"], "archetype": arch,
        "band": {"pitch_hz": list(pitch),
                 "rate_syl_s": PACE_TARGET.get(arch, 2.2),
                 "dispersion": ("low" if arch in DISP_WANT_LOW else "high"),
                 "f0std_hz": list(tex["f0std"]),
                 "flatness": tex["flatness"],
                 "delivery": prof.get("delivery", ""),
                 "vendor_tags": list(ARCHETYPE_TAGS.get(arch, ()))},
        "evidence": {"books": g["books"], "dialogue_lines": g["dialogue_lines"],
                     "pace_note": g["pace_note"],
                     "relationships": [(r["with"], r["contrast"])
                                       for r in g["relationships"][:3]]},
        "queries": g["queries"], "vetoes": g["vetoes"],
    }


def fit_score(measured: dict, band: dict) -> dict:
    """Measured sample vs predicted band -> fit breakdown. Quantitative."""
    lo, hi = band["pitch_hz"]
    f0 = measured.get("f0_median_hz")
    parts, notes = {}, []
    if f0:
        mid = (lo + hi) / 2
        half = max((hi - lo) / 2, 20)
        pitch_s = max(0.0, 1.0 - abs(f0 - mid) / (2 * half))
        parts["pitch"] = round(pitch_s * 5, 2)
        notes.append(f"F0 {f0}Hz vs band {lo}-{hi}")
    else:
        parts["pitch"] = 0.0
        notes.append("unpitchable sample (whisper?) — no pitch evidence")
    rate = measured.get("syllables_per_sec")
    if rate:
        tgt = band["rate_syl_s"]
        rate_s = max(0.0, 1.0 - abs(rate - tgt) / tgt)
        parts["rate"] = round(rate_s * 3, 2)
        notes.append(f"rate {rate}/s vs target {tgt}/s")
    else:
        parts["rate"] = 0.0
    disp = measured.get("formant_dispersion_hz")
    if disp:
        # direction only until dispersion targets are calibrated per type
        parts["dispersion"] = round(1.0 if
                                    (band["dispersion"] == "low") == (disp < 1000)
                                    else 0.0, 2)
        notes.append(f"dispersion {disp}Hz (want {band['dispersion']})")
    total = round(sum(parts.values()), 2)
    n_p = measured.get("n_pauses", 0) or 0
    dur = measured.get("duration_s", 0) or 0
    if dur:
        ppm = n_p / (dur / 60)
        parts["pauses"] = round(min(1.0, ppm / 40.0), 2)
        notes.append(f"{ppm:.0f} pauses/min (elders pause)")
        total = round(total + parts["pauses"], 2)
    # texture/motivation: flatness + pitch steadiness vs archetype targets.
    # Demonic is flat+harch; playful is varied+tonal (Morton MS rules).
    tlo, thi = band.get("f0std_hz", [5, 40])
    std = measured.get("f0_std_hz")
    if std is not None:
        std_s = 1.0 if tlo <= std <= thi else max(
            0.0, 1.0 - (min(abs(std - tlo), abs(std - thi)) / 30.0))
        parts["steadiness"] = round(std_s * 1.5, 2)
        notes.append(f"f0std {std}Hz vs target {tlo}-{thi}")
    flat = measured.get("flatness_median")
    want_flat = band.get("flatness", "mid")
    if flat is not None:
        exp = {"high": 0.3, "mid": 0.2, "low": 0.12}[want_flat]
        flat_s = max(0.0, 1.0 - abs(flat - exp) / 0.25)
        parts["texture"] = round(flat_s * 1.5, 2)
        notes.append(f"flatness {flat:.3f} (want {want_flat})")
    total = round(sum(parts.values()), 2)
    return {"fit": total, "max": 13.0, "parts": parts, "notes": notes}


def render_recipe(measured_rate: float | None, arch: str,
                  mary_rate_delta: float = 0.0) -> dict:
    """Character tempo + voice baseline -> free-tier prosody knobs ($0).
    speed bridges measured voice rate to character target; MARY delta trims.
    Fish free tier accepts speed 0.5-2.0, volume, temperature (docs: TTS)."""
    tgt = PACE_TARGET.get(arch, 2.2)
    if measured_rate:
        speed = tgt / max(measured_rate, 0.5)
    else:
        speed = 0.85 + mary_rate_delta * 0.5
    speed = round(max(0.5, min(1.3, speed)), 2)  # sleep lane never hurries
    return {"model": "s2.1-pro-free", "prosody": {"speed": speed},
            "temperature": 0.6, "usd": 0.0,
            "why": f"target {tgt} syl/s for {arch}" +
                   (f"; voice runs {measured_rate}/s" if measured_rate else "")}


def main():
    channel, name = (sys.argv[1:3] + ["folk-and-fable", "Tortoise"])[:2]
    band = derive_band(channel, name)
    print(json.dumps(band, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
