"""Bradley-Terry voice fit — the ML problem, stated honestly.

Problem: P(voice V fits character profile C), calibrated from the
owner's pairwise rankings. Features: voice tags + anchor overlap +
acoustic band + chair/function context. No training infra: batch
logistic fit over stored pairs (mini-LoRe spirit — shared low-dim
weights, few data), pure stdlib.

Character profiles come from two places:
  ours: dramatis (role/age/gender/dialogue) + channel chairs
  theirs: characters packs (persona, modulators, misinterpretation_rule,
  motivations, archetype, dramatic_core) — matched by name.

Verdict shape unifies with characters voice_battle: {state hot..cold,
action double_down|experiment|pivot} = our fuse() verdicts. One fork
killed from our side; theirs already matches.
"""
from __future__ import annotations

import math

# feature weights: fitted by fit() below; defaults = priors until pairs exist
WEIGHTS: dict[str, float] = {}
N_PAIRS = 0


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


def voice_features(tags: list, anchor_overlap: int = 0,
                   sleep_band_ok: bool = True) -> dict[str, float]:
    """Sparse feature vector for one voice. Tags are binary indicators."""
    f: dict[str, float] = {}
    for t in tags or []:
        t = str(t).strip().lower()
        if len(t) >= 3:
            f[f"tag:{t}"] = 1.0
    f["anchor_overlap"] = float(anchor_overlap)
    f["sleep_band"] = 1.0 if sleep_band_ok else 0.0
    return f


def profile_features(profile: dict) -> dict[str, float]:
    """Character-graph profile → desired-feature weights (the query side).
    Pack fields (modulators, misinterpretation_rule, motivations) bias
    toward delivery tags; dramatis fields (age/gender/role) toward bands."""
    f: dict[str, float] = {}
    for m in profile.get("modulator_range") or []:
        f[f"want:{str(m).lower()}"] = 1.0
    for k in ("age", "gender", "role", "archetype"):
        v = profile.get(k)
        if v:
            f[f"want:{str(v).lower()}"] = 1.0
    return f


def _score(feats: dict[str, float], w: dict[str, float]) -> float:
    return sum(v * w.get(k, 0.0) for k, v in feats.items())


def fit(pairs: list[dict], iters: int = 200, lr: float = 0.1) -> dict:
    """Batch BT fit: pairs of (winner_feats, loser_feats) →
    weights maximizing pairwise log-likelihood. Returns weights + stats."""
    w: dict[str, float] = {}
    for _ in range(iters):
        for p in pairs:
            wf, lf = p["winner"], p["loser"]
            keys = set(wf) | set(lf)
            s = _sigmoid(_score(wf, w) - _score(lf, w))
            for k in keys:
                w[k] = w.get(k, 0.0) + lr * (1 - s) * (
                    wf.get(k, 0.0) - lf.get(k, 0.0))
    # accuracy on training pairs (honest in-sample report)
    right = sum(1 for p in pairs
                if _score(p["winner"], w) > _score(p["loser"], w))
    return {"weights": {k: round(v, 3) for k, v in w.items()},
            "pairs": len(pairs),
            "train_accuracy": round(right / max(1, len(pairs)), 3)}


def p_beats(a: dict[str, float], b: dict[str, float],
            w: dict[str, float]) -> float:
    """P(a preferred over b). The calibrated pick rule."""
    return round(_sigmoid(_score(a, w) - _score(b, w)), 3)


def verdict_from_margin(margin: float, n: int) -> dict:
    """Unified verdict (matches characters voice_battle shape)."""
    if margin >= 3.0 and n >= 5:
        return {"state": "hot", "action": "double_down"}
    if margin >= 1.5:
        return {"state": "growing", "action": "double_down"}
    if margin >= 0.5:
        return {"state": "steady", "action": "experiment"}
    if margin >= 0.0:
        return {"state": "cooling", "action": "experiment"}
    return {"state": "cold", "action": "pivot"}
