"""Availability — real slot-finding for the tradie brain.

Cleanroom port of the AIReceptionist availability pattern (AGPL — patterns
only, no pasted code): given working hours + preferences + already-scheduled
jobs, propose concrete slots the voice agent can speak and the customer can
confirm. Pure functions (Rule 3): pass everything in, no I/O.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def working_windows(hours_cfg: dict[str, str], day: datetime) -> list[tuple[datetime, datetime]]:
    """Working windows for a date from kernel hours like {"monday-friday": "08:00-18:00"}."""
    weekday = day.weekday()  # 0=Mon
    keys = []
    if weekday < 5:
        keys += ["monday-friday", ["monday", "tuesday", "wednesday", "thursday", "friday"][weekday]]
    elif weekday == 5:
        keys += ["saturday"]
    else:
        keys += ["sunday"]
    for k in keys:
        spec = hours_cfg.get(k, "")
        if not spec or spec.strip().lower() == "closed":
            continue
        try:
            start_s, end_s = spec.split("-")
            base = day.replace(hour=0, minute=0, second=0, microsecond=0)
            return [(base + timedelta(hours=_parse_hhmm(start_s.strip()).hour,
                                      minutes=_parse_hhmm(start_s.strip()).minute),
                     base + timedelta(hours=_parse_hhmm(end_s.strip()).hour,
                                      minutes=_parse_hhmm(end_s.strip()).minute))]
        except ValueError:
            continue
    return []


def find_slots(kernel_cfg: dict[str, Any], busy: list[tuple[datetime, datetime]],
               duration_min: int = 120, days_ahead: int = 7, limit: int = 5,
               now: datetime | None = None) -> list[dict[str, Any]]:
    """Propose up to `limit` free slots. Prefers preferred_slots (morning-first),
    skips busy overlaps, never proposes the past."""
    now = now or datetime.now(timezone.utc)
    prefs = kernel_cfg.get("preferences") or {}
    hours_cfg = kernel_cfg.get("hours") or {"monday-friday": "08:00-18:00"}
    morning_first = "morning" in (prefs.get("preferred_slots") or [])
    dur = timedelta(minutes=duration_min)
    step = timedelta(minutes=30)
    out: list[dict[str, Any]] = []
    day = now
    for _ in range(days_ahead + 1):
        for ws, we in working_windows(hours_cfg, day):
            t = max(ws, now + timedelta(hours=1))  # min 1h lead time
            # align to half hour
            t = t.replace(minute=(30 if t.minute >= 30 else 0), second=0, microsecond=0)
            if t.minute == 30 and t < ws + step:
                t = ws
            while t + dur <= we and len(out) < limit:
                if not any(b0 < t + dur and t < b1 for b0, b1 in busy):
                    label = t.strftime("%a %d %b")
                    part = "morning" if t.hour < 12 else "afternoon" if t.hour < 17 else "evening"
                    out.append({"start": t.isoformat(), "label": f"{label} {part} ({t.strftime('%H:%M')})",
                                "part": part})
                t += step
        if len(out) >= limit:
            break
        day = (day + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if morning_first:
        out.sort(key=lambda s: (0 if s["part"] == "morning" else 1, s["start"]))
    return out[:limit]
