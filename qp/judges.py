"""Jev-shaped typed judges, rule-based v0. Same contracts a Jev provider
will serve later: Choice / Score / Noul with probabilities + confidence.
Code owns thresholds; judges only answer narrow questions. Unknown or
empty input yields uncertainty, never confidence."""
from __future__ import annotations

import re

INTENTS = ("reply", "transact", "spam", "fyi", "other")
URGENCY_LEGEND = ("can wait", "needs attention soon", "needs attention today")

_REPLY = re.compile(r"\b(help|support|issue|question|approve|accept|action required|invoice|order|refund|book|quote)\b", re.I)
_SPAM = re.compile(r"\b(crypto giveaway|double your|act now|limited offer|winner|claim your prize)\b", re.I)
_URGENT = re.compile(r"\b(urgent|asap|today|immediately|deadline|emergency|charged twice)\b", re.I)
_OVERRIDE = re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules)|disregard\s+(all\s+)?(previous|prior|system)|you\s+are\s+now\s+(a|an|my)\s+|do\s+not\s+tell\s+(the\s+)?(user|owner|human)", re.I)


def _conf(margin: float) -> float:
    return max(0.0, min(1.0, margin))


def intent_choice(text: str) -> dict:
    """Choice over INTENTS. Always offers other; empty text is uncertain."""
    t = (text or "").strip()
    if not t:
        n = len(INTENTS)
        return {"choice": "other", "probabilities": {k: round(1 / n, 3) for k in INTENTS},
                "confidence": 0.0}
    scores = {"reply": 0.4 if _REPLY.search(t) else 0.0,
              "transact": 0.3 if re.search(r"\b(pay|buy|invoice|order|subscribe)\b", t, re.I) else 0.0,
              "spam": 0.9 if _SPAM.search(t) else 0.0,
              "fyi": 0.3, "other": 0.25}
    if _OVERRIDE.search(t):
        scores = {"reply": 0.0, "transact": 0.0, "spam": 0.0, "fyi": 0.0, "other": 1.0}
        return {"choice": "other", "probabilities": scores, "confidence": 0.9,
                "flag": "override_attempt"}
    total = sum(scores.values())
    probs = {k: round(v / total, 3) for k, v in scores.items()}
    top = max(probs, key=probs.get)
    runner = sorted(probs.values())[-2]
    return {"choice": top, "probabilities": probs, "confidence": round(_conf(probs[top] - runner), 3)}


def urgency_score(text: str) -> dict:
    """Score 0..2 over URGENCY_LEGEND. Probability-weighted; may land between."""
    t = (text or "").strip()
    if not t:
        return {"score": 0.0, "legend": list(URGENCY_LEGEND),
                "probabilities": {"0": 0.34, "1": 0.33, "2": 0.33}, "confidence": 0.0}
    hits = len(_URGENT.findall(t))
    p2 = min(0.9, 0.2 + 0.35 * hits) if hits else 0.05
    p1 = 0.5 if _REPLY.search(t) and not hits else 0.2
    p0 = max(0.05, 1.0 - p2 - p1)
    total = p0 + p1 + p2
    probs = {"0": round(p0 / total, 3), "1": round(p1 / total, 3), "2": round(p2 / total, 3)}
    score = round(probs["1"] * 1 + probs["2"] * 2, 3)
    return {"score": score, "legend": list(URGENCY_LEGEND),
            "probabilities": probs, "confidence": round(_conf(max(probs.values()) - 0.33), 3)}


def needs_human_noul(text: str, consequence: str = "low") -> dict:
    """Probability this item needs a human. High-consequence defaults high."""
    if consequence in ("money", "send", "identity", "secret"):
        return {"noul": 1.0, "reason": f"never-auto class: {consequence}"}
    intent = intent_choice(text)
    urg = urgency_score(text)
    if intent.get("flag") == "override_attempt":
        return {"noul": 1.0, "reason": "override attempt -> quarantine review"}
    p = 0.15 + 0.5 * urg["score"] / 2 + (0.2 if intent["choice"] in ("reply", "transact") else 0.0)
    return {"noul": round(min(1.0, p), 3),
            "reason": f"intent={intent['choice']} urgency={urg['score']}"}


def guardrail_noul(text: str) -> dict:
    """Probability the text attacks the harness. Near 0.5 = uncertain."""
    t = text or ""
    if _OVERRIDE.search(t):
        return {"noul": 0.95, "reason": "override pattern"}
    if re.search(r"\b(send|show|reveal|forward|list)\b[^.]{0,60}\b(api\s*keys?|passwords?|secrets?|tokens?)\b", t, re.I):
        return {"noul": 0.9, "reason": "exfil pattern"}
    return {"noul": 0.05, "reason": "no pattern"}
