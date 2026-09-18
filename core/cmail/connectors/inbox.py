from __future__ import annotations

from typing import Any

from .base import Observation
from qp.judges import guardrail_noul, intent_choice, needs_human_noul, urgency_score


class InboxConnector:
    """Triage for already-fetched message batches. Fetching itself stays
    behind provider creds; this connector only judges. Anything scoring a
    guardrail hit is quarantined (downgrade-only) and never triaged."""

    kind = "inbox"

    def observe(self, desired: dict[str, Any]) -> Observation:
        messages = desired.get("messages")
        provider = desired.get("provider", "inbox")
        if not isinstance(messages, list) or not messages:
            return Observation("MISSING", f"No {provider} batch to triage", executor="HUMAN",
                               human_title=f"Connect {provider} inbox",
                               human_instructions="Connect the inbox provider (OAuth/tokens in vault), fetch a batch, then re-run reconcile. Fetching needs creds; judging does not.",
                               estimate_seconds=300, priority=55)
        items, needy, quarantined = [], 0, 0
        try:
            for m in messages:
                if not isinstance(m, dict):
                    continue
                text = f"{m.get('subject', '')}\n{m.get('body', '')}"
                g = guardrail_noul(text)
                if g["noul"] >= 0.5:
                    quarantined += 1
                    items.append({"id": m.get("id"), "quarantined": True,
                                  "reason": g["reason"]})
                    continue
                intent = intent_choice(text)
                urg = urgency_score(text)
                nh = needs_human_noul(text)
                if nh["noul"] >= 0.5:
                    needy += 1
                items.append({"id": m.get("id"), "intent": intent["choice"],
                              "intent_conf": intent["confidence"],
                              "urgency": urg["score"], "needs_human": nh["noul"]})
        except Exception as exc:
            return Observation("UNKNOWN", f"Triage failed safely: {exc}",
                               observed={"provider": provider})
        observed: dict[str, Any] = {"provider": provider, "total": len(items),
                                    "need_human": needy, "quarantined": quarantined,
                                    "items": items[:50]}
        if quarantined and not needy:
            return Observation("BLOCKED", f"{quarantined} quarantined, nothing actionable",
                               observed=observed, executor="HUMAN",
                               human_title="Review quarantined items",
                               human_instructions="Items were quarantined by the guardrail (downgrade-only). Review them; they never re-enter the queue automatically.",
                               estimate_seconds=180, priority=90)
        if needy:
            return Observation("MISSING", f"{needy} of {len(items)} need a human",
                               observed=observed, executor="HUMAN",
                               human_title=f"Triage {needy} inbox items",
                               human_instructions="Open the ops lens, answer each item (digit per task). Low-confidence items are marked.",
                               estimate_seconds=60 * needy, priority=65)
        return Observation("READY", f"Inbox triaged: {len(items)} items, none need you",
                           observed=observed)
