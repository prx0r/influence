"""Chat commands. No fake LLM: only explicit graph operations. Everything else gets usage."""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)

HELP = ("commands:\n"
        "/add <slug> <domain> — import domain as influencer + reconcile\n"
        "/status — projects, stages, open tasks\n"
        "/help — this")


def handle_chat(message: str) -> dict:
    parts = message.strip().split()
    if not parts:
        return {"reply": HELP}
    cmd = parts[0].lower()
    if cmd == "/help":
        return {"reply": HELP}
    if cmd == "/status":
        from dash.store import live_state
        d = live_state()
        lines = [f"{len(d['influencers'])} influencers, {len(d['tasks'])} open tasks"]
        for i in d["influencers"]:
            ready = sum(1 for r in i["resources"] if r["status"] == "READY")
            lines.append(f"· {i['slug']} [{i['stage']}] {ready}/{len(i['resources'])} READY")
        return {"reply": "\n".join(lines)}
    if cmd == "/add":
        if len(parts) != 3:
            return {"reply": "usage: /add <slug> <domain>"}
        _, slug, domain = parts
        if not slug.replace("-", "").replace("_", "").isalnum() or "." not in domain:
            return {"reply": "bad slug or domain"}
        import sys
        sys.path.insert(0, PARENT)
        from dash.import_domains import import_domain
        import_domain(slug, slug, domain)
        from dash.store import live_state
        d = live_state()
        inf = next((i for i in d["influencers"] if i["slug"] == slug), None)
        if not inf:
            return {"reply": f"added {slug} but state missing — check reconcile"}
        mine = [t for t in d["tasks"] if t["influencer"] == slug]
        return {"reply": f"added {slug} [{inf['stage']}]. {len(mine)} open tasks.", "refresh": True}
    return {"reply": f"unknown command. {HELP}"}
