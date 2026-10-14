"""Voice judging — delivery stats vs sleep bands. Ported pattern from
characters (audition/voice_judge.py + theory/vibe-bands.json + domains.json
sleep recipe). Their finding, adopted: sleep = slow + dark + drowsy glides,
NOT flat. Fish knobs are the only inputs (cue/temperature/speed/volume);
Hz/formants are measurements for judging only.

Needs numpy (system python3 has it; stevejobless venv does not — run
judging from automation/shell, not the dash server process).

SLEEP_BANDS from characters measurements (sleep male/female, transfer tests).
"""
from __future__ import annotations

SLEEP_BANDS = {
    "wpm": (135, 170),        # measured sleep 152-154; neutral ~197
    "f0_std_max": 120.0,       # drowsy glides allowed, not wild swings
    "voiced_min": 0.25,        # sleep delivery is sparse + pausy
    "voiced_max": 0.75,        # above = talkative, wrong room
    "mean_range": (100, 300),  # sane human band, male or female
}


def measure(path: str, text: str = "") -> dict:
    """F0/energy/duration stats for one clip. Requires numpy."""
    import wave
    import numpy as _np
    w = wave.open(path)
    n = w.getnframes()
    sr = w.getframerate()
    x = _np.frombuffer(w.readframes(n), dtype=_np.int16).astype(float)
    dur = n / sr
    x = x / max(1, float(_np.abs(x).max()))
    fl, hop = int(sr * 0.03), int(sr * 0.01)
    f0s = []
    for i in range(0, len(x) - fl, hop):
        f = x[i:i + fl] * _np.hanning(fl)
        r = _np.correlate(f, f, "full")[fl - 1:]
        r /= max(1e-9, r[0])
        lo, hi = int(sr / 500), int(sr / 50)
        k = int(_np.argmax(r[lo:hi])) + lo
        f0s.append(sr / k if r[k] > 0.45 else 0)
    f0s = _np.array(f0s)
    v = f0s[f0s > 0]
    out = {"duration_s": round(dur, 1),
           "f0_mean": round(float(v.mean()), 0) if len(v) else 0,
           "f0_std": round(float(v.std()), 0) if len(v) else 0,
           "f0_span_st": round(float(12 * _np.log2(v.max() / v.min())), 1)
           if len(v) else 0,
           "voiced": round(len(v) / max(1, len(f0s)), 2)}
    if text:
        out["wpm"] = round(len(text.split()) / max(1, dur) * 60, 0)
    return out


def sleep_fit(stats: dict) -> dict:
    """Score delivery against SLEEP_BANDS. 100 = textbook sleep delivery."""
    score, notes = 100.0, []
    wpm = stats.get("wpm")
    if wpm:
        lo, hi = SLEEP_BANDS["wpm"]
        if wpm < lo:
            score -= 10
            notes.append(f"slower than sleep band ({wpm}wpm)")
        elif wpm > hi:
            score -= min(25, (wpm - hi) / 4)
            notes.append(f"faster than sleep band ({wpm}wpm)")
    if stats.get("f0_std", 0) > SLEEP_BANDS["f0_std_max"]:
        score -= 15
        notes.append("pitch swings wide (wakes the room)")
    v = stats.get("voiced", 0.5)
    if v < SLEEP_BANDS["voiced_min"]:
        score -= 10
        notes.append("mostly silence (check render)")
    elif v > SLEEP_BANDS["voiced_max"]:
        score -= 15
        notes.append("dense delivery, no sleep pauses")
    mn = stats.get("f0_mean", 150)
    if not (SLEEP_BANDS["mean_range"][0] <= mn <= SLEEP_BANDS["mean_range"][1]):
        score -= 10
        notes.append("mean pitch outside human band (measure noise?)")
    return {"score": round(max(0, score), 0), "notes": notes,
            "bands": "sleep v1 (characters transfer tests)"}
