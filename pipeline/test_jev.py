"""Tests for jev.py. Pure, no network, no spend."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from jev import (engagement_score, rank_videos, channel_health, fuse,
                 rsi, channel_momentum)


def test_engagement_prefers_subs_and_retention():
    a = {"views": 1000, "likes": 100, "comments": 20, "shares": 10,
         "subs_gained": 50, "avg_view_duration": 400, "duration": 600}
    b = {"views": 10000, "likes": 100, "comments": 5, "shares": 0,
         "subs_gained": 2, "avg_view_duration": 60, "duration": 600}
    assert engagement_score(a)["score"] > engagement_score(b)["score"]


def test_rank_diversity_penalizes_runs():
    vs = [{"title": f"v{i}", "format": "tale", "views": 1000,
           "likes": 50, "avg_view_duration": 300, "duration": 600}
          for i in range(3)]
    r = rank_videos(vs)
    assert r[0]["score"] >= r[1]["score"] >= r[2]["score"]
    assert "diversity_penalty" in r[1]


def test_channel_health_verdicts():
    assert channel_health([])["verdict"] == "no_data"
    good = [{"title": "t", "format": "tale", "views": 5000, "likes": 500,
             "comments": 100, "shares": 50, "subs_gained": 200,
             "avg_view_duration": 500, "duration": 600}]
    h = channel_health(good)
    assert h["verdict"] in ("strong", "healthy"), h


def test_fuse_weights_and_verdicts():
    sigs = [{"source": "youtube.stats", "content_id": "v1", "score_0_100": 80},
            {"source": "watch.retention", "content_id": "v1", "score_0_100": 60},
            {"source": "nope.zone", "content_id": "v1", "score_0_100": 100}]
    f = fuse(sigs)
    assert set(f["v1"]["signals"]) == {"youtube.stats", "watch.retention"}
    assert 60 <= f["v1"]["score"] <= 80
    assert f["v1"]["verdict"] in ("hot", "growing", "steady")


def test_rsi_and_momentum():
    up = [float(100 + i * 10) for i in range(20)]
    assert channel_momentum(up)["signal"] in ("surging", "rising")
    down = [float(300 - i * 10) for i in range(20)]
    assert channel_momentum(down)["signal"] in ("fading", "cooling")
    assert channel_momentum([1.0, 2.0])["signal"] == "too_little_data"
    assert len(rsi(up)) == len(up)
