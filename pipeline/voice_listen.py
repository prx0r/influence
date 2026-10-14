"""Listen to candidate samples (their acoustic.py, reimplemented without
librosa — numpy + scipy + ffmpeg only). Measures what tags can't say:
F0 median/range, formant dispersion (the honest size cue), speech rate
(transcript-free syllable nuclei), pauses, jitter, brightness.

Usage: python3 pipeline/voice_listen.py <mp3-or-url> [more...]
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

SR = 16000


def _fetch(src: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix="listen_"))
    out = d / "a.mp3"
    if src.startswith("http"):
        urllib.request.urlretrieve(src, out)
    else:
        out = Path(src)
    wav = d / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(out),
                    "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le",
                    str(wav)], check=True, timeout=120)
    return wav


def _frames(y: np.ndarray, n: int = 400, hop: int = 160):
    return np.stack([y[i:i + n] for i in range(0, len(y) - n, hop)])


def f0_track(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Autocorrelation F0 per 25ms frame (60-500Hz), median-anchored to
    kill octave jumps. Returns hz, voiced mask."""
    fr = _frames(y) * np.hamming(400)
    fr = fr - fr.mean(axis=1, keepdims=True)
    hz = np.full(len(fr), np.nan)
    per = np.zeros(len(fr))
    lo, hi = SR // 500, SR // 60  # lag bounds
    for i, f in enumerate(fr):
        if np.max(np.abs(f)) < 1e-4:
            continue
        ac = np.correlate(f, f, mode="full")[len(f) - 1:]
        ac = ac / max(ac[0], 1e-9)
        seg = ac[lo:hi]
        k = int(np.argmax(seg)) + lo
        b = seg[k - lo]
        if 0 < k - lo < len(seg) - 1:
            a, c = seg[k - lo - 1], seg[k - lo + 1]
            d = 0.5 * (a - c) / max(a - 2 * b + c, 1e-9)
            k = k + max(-1.0, min(1.0, d))
        hz[i] = SR / k
        per[i] = b
    voiced = per > 0.32
    # octave guard: frames >7 semitones from the rolling median are jumps
    h = hz.copy()
    med = np.nanmedian(h[voiced]) if np.any(voiced) else np.nan
    if not np.isnan(med):
        h[np.abs(12 * np.log2(h / med)) > 7] = np.nan
        voiced = voiced & ~np.isnan(h)
        return h, voiced
    return hz, voiced


def formants(y: np.ndarray) -> list:
    """LPC roots -> F1-F3 (their method, numpy only). Mid-clip voiced frame."""
    mid = len(y) // 2
    frame = y[mid:mid + 1024]
    if len(frame) < 1024 or np.max(np.abs(frame)) < 1e-4:
        return []
    frame = frame * np.hamming(1024)
    corr = np.correlate(frame, frame, mode="full")
    corr = corr[len(corr) // 2:]
    order = 18
    a = np.zeros(order + 1)
    a[0] = 1.0
    e = corr[0]
    for i in range(1, order + 1):
        lam = sum(a[j] * corr[i - j] for j in range(i))
        k = -lam / e if e > 0 else 0
        an = a.copy()
        for j in range(1, i):
            an[j] = a[j] + k * a[i - j]
        an[i] = k
        a = an
        e *= (1 - k * k)
        if e <= 0:
            break
    roots = np.roots(a)
    roots = roots[np.imag(roots) > 0]
    freqs = sorted(np.arctan2(np.imag(roots), np.real(roots)) * (SR / (2 * np.pi)))
    return [round(float(f), 0) for f in freqs[:3] if 200 < f < 4000]


def listen(src: str) -> dict:
    wav = _fetch(src)
    import wave
    with wave.open(str(wav), "rb") as w:
        raw = w.readframes(w.getnframes())
    y = np.frombuffer(raw, dtype=np.int16).astype(float) / 32768.0
    dur = len(y) / SR
    hz, voiced = f0_track(y)
    vf = hz[voiced & ~np.isnan(hz)]
    # energy nuclei (syllables): RMS peaks, >=150ms apart
    fr = _frames(np.abs(y)) ** 2
    rms = np.sqrt(fr.mean(axis=1))
    db = 20 * np.log10(rms + 1e-9)
    thr = np.percentile(db[db > -60], 70) if np.any(db > -60) else -30
    peaks, last = 0, -99
    for i in range(1, len(db) - 1):
        if db[i] > thr and db[i] >= db[i - 1] and db[i] >= db[i + 1]:
            if i - last >= 15:
                peaks += 1
                last = i
    # pauses: < -35dB runs > 150ms
    sil = db < -35
    n_pause, run = 0, 0
    for s in sil:
        if s:
            run += 1
        else:
            if run >= 15:
                n_pause += 1
            run = 0
    # spectral centroid + flatness (tonal vs harsh/broadband)
    spec = np.abs(np.fft.rfft(_frames(y) * np.hamming(400), axis=1))
    freqs = np.fft.rfftfreq(400, 1 / SR)
    cent = (spec * freqs).sum(axis=1) / spec.sum(axis=1).clip(min=1e-9)
    _sp = spec + 1e-9
    flat = np.exp(np.log(_sp).mean(axis=1)) / _sp.mean(axis=1)
    jit = round(float(np.mean(np.abs(np.diff(vf)) / vf[:-1]) * 100), 2) \
        if len(vf) > 10 else None
    fm = formants(y)
    disp = round(float(np.mean(np.diff(fm))), 0) if len(fm) >= 2 else None
    return {
        "duration_s": round(dur, 2),
        "f0_median_hz": round(float(np.median(vf)), 1) if len(vf) else None,
        "f0_mean_hz": round(float(np.mean(vf)), 1) if len(vf) else None,
        "f0_std_hz": round(float(np.std(vf)), 1) if len(vf) else None,
        "f0_min_hz": round(float(np.min(vf)), 1) if len(vf) else None,
        "f0_max_hz": round(float(np.max(vf)), 1) if len(vf) else None,
        "voiced_frac": round(float(voiced.mean()), 3),
        "formants_hz": fm,
        "formant_dispersion_hz": disp,
        "syllables_per_sec": round(peaks / dur, 2) if dur else None,
        "n_pauses": n_pause,
        "centroid_mean_hz": round(float(np.mean(cent)), 0),
        "flatness_median": round(float(np.median(flat)), 4),
        "jitter_pct": jit,
    }


def main():
    for src in sys.argv[1:]:
        try:
            m = listen(src)
            print(f"### {src[:70]}")
            print(json.dumps(m, indent=1))
        except Exception as e:
            print(f"### {src[:70]} FAILED {e}"[:150])


if __name__ == "__main__":
    main()
