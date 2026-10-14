"""voice_judge reads Fish MP3s (and stereo) correctly. Needs numpy + ffmpeg."""
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
np = pytest.importorskip("numpy")
pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"),
                                reason="ffmpeg missing")

import voice_judge as vj  # noqa: E402


def _tone(path, hz=180, secs=2, ch=1):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=frequency={hz}:duration={secs}", "-ac", str(ch),
                    path], check=True)


@pytest.mark.parametrize("ext,ch", [("mp3", 1), ("wav", 2), ("wav", 1)])
def test_measure_any_format(tmp_path, ext, ch):
    p = str(tmp_path / f"t.{ext}")
    _tone(p, ch=ch)
    st = vj.measure(p, "one two three four five")
    assert 1.8 <= st["duration_s"] <= 2.2
    assert 170 <= st["f0_mean"] <= 190, st
    assert st["voiced"] > 0.8


def test_sleep_fit_scores():
    good = {"wpm": 150, "f0_std": 30, "voiced": 0.5, "f0_mean": 140}
    bad = {"wpm": 230, "f0_std": 160, "voiced": 0.9, "f0_mean": 140}
    assert vj.sleep_fit(good)["score"] == 100
    assert vj.sleep_fit(bad)["score"] < 60
