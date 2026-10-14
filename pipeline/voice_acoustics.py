"""Voice acoustics — listen, don't trust tags.

Fish descriptions lie (a "deep" voice at 250Hz mean, "calm" at high
variance). This module downloads a voice's sample audio once, measures
delivery stats (voice_judge.measure: F0 mean/std/span, voiced density,
wpm where text known), and caches per voice ID. propose() and the BT
model use MEASURED bands; tag claims that contradict measurement get
flagged, never trusted.

Needs numpy + ffmpeg (system python3 has both; dash venv does not —
measure from automation/shell, read cache from anywhere).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.normpath(os.path.join(_HERE, "..", "studio",
                                           "voice-acoustics.json"))


def _load_cache() -> dict:
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save_cache(d: dict) -> None:
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, CACHE_PATH)


def _download_sample(url: str) -> str | None:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "influence-acoustics/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            if int(r.headers.get("Content-Length", "0") or 0) > 8_000_000:
                return None
            data = r.read(8_000_000)
        fd, path = tempfile.mkstemp(suffix=".snd")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path
    except Exception:
        return None


def measure_voice(voice_id: str, sample_url: str = "",
                  text: str = "", force: bool = False) -> dict:
    """Measure one voice's sample; cached by voice ID. Returns stats +
    tag-lie flags (claimed vs measured)."""
    cache = _load_cache()
    if not force and voice_id in cache:
        return {"ok": True, "cached": True, **cache[voice_id]}
    if not sample_url:
        return {"ok": False, "reason": "no sample audio"}
    import sys as _s
    _s.path.insert(0, _HERE)
    from voice_judge import measure as _measure, sleep_fit as _fit
    src = _download_sample(sample_url)
    if not src:
        return {"ok": False, "reason": "sample download failed"}
    wav = src + ".wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", src, "-ar", "16000",
             "-ac", "1", wav], check=True, timeout=120)
        stats = _measure(wav, text)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"measure failed: {e}"[:150]}
    finally:
        for p in (src, wav):
            try:
                os.remove(p)
            except OSError:
                pass
    entry = {"stats": stats, "sleep_fit": _fit(stats)}
    cache[voice_id] = entry
    _save_cache(cache)
    return {"ok": True, "cached": False, **entry}


def tag_lies(claimed_tags: list, stats: dict) -> list[str]:
    """Where Fish tags contradict measurement. Evidence over marketing."""
    lies = []
    claimed = {str(t).strip().lower() for t in claimed_tags or []}
    mean = stats.get("f0_mean") or 0
    std = stats.get("f0_std") or 0
    if mean and ({"deep", "low", "bass"} & claimed) and mean > 200:
        lies.append(f"claims deep/low but measures {mean:.0f}Hz mean")
    if mean and ({"high", "soprano", "bright"} & claimed) and mean < 160:
        lies.append(f"claims high/bright but measures {mean:.0f}Hz mean")
    if ({"calm", "steady", "measured"} & claimed) and std > 120:
        lies.append(f"claims calm/steady but pitch std {std:.0f}Hz (wild)")
    if ({"whisper", "soft", "breathy"} & claimed) and stats.get(
            "voiced", 0.5) > 0.85:
        lies.append("claims whisper/soft but delivery is dense (no pauses)")
    if ({"slow", "unhurried"} & claimed) and (stats.get("wpm") or 0) > 185:
        lies.append(f"claims slow but speaks {stats.get('wpm'):.0f}wpm")
    return lies
