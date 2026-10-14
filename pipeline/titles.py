"""Title engine — rule-based drafts from tale metadata + channel recipe.

No LLM, no spend, deterministic. Formulas live in channel records
(formats[] + pitch); this renders candidates. Human picks train future
drafts (picks stored per channel; preferred patterns rank first).
"""
from __future__ import annotations

import re


def _clean(s: str) -> str:
    s = re.sub(r"^\d+[\-_ ]+", "", str(s or ""))
    s = re.sub(r"[-_]+", " ", s).strip()
    return s


def draft(title: str, tradition: str = "", duration: str = "",
          picked_patterns: list | None = None) -> list[dict]:
    """3 title candidates. Each carries its formula for learning."""
    base = _clean(title).title()
    trad = _clean(tradition)
    dur = duration or ""
    cands = [
        {"title": f"{trad + ': ' if trad else ''}{base} — Sleep Reading"
                  f"{' | ' + dur if dur else ''}".strip(),
         "formula": "tradition-story-duration", "reason": "searchable + ritual"},
        {"title": f"Sleep Reading: {base}"
                  f"{' (' + trad + ')' if trad else ''}",
         "formula": "brand-first", "reason": "channel brand leads"},
        {"title": f"{base} — A Sleepy Tale{dur and ' | ' + dur or ''}",
         "formula": "story-mood", "reason": "shortest, browse-friendly"},
    ]
    if picked_patterns:
        pref = [p for p in picked_patterns if isinstance(p, str)]
        cands.sort(key=lambda c: 0 if c["formula"] in pref else 1)
    return cands
