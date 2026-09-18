"""Chat agent. Deterministic loop over the graph — no fake LLM: every answer
is computed from live state, MCP tools, HLoop, or the journal.

Commands:
  /add <slug> <domain> — import domain as influencer + reconcile
  /status — projects, stages, open tasks (urgency-sorted)
  tasks — human queue with urgency + digits
  decide <task_id> <digit> — present + decide in one turn (intent only)
  receipt <receipt_id> — verify a receipt independently
  influencer <slug> — resources + stage
  products — product registry
  /help — this

Anything else is routed by intent judges to the closest capability, with
confidence shown. An LLM narrator can sit on top later; the verbs below
are the agent regardless of who phrases them.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

HELP = ("commands:\n"
        "/add <slug> <domain> — import domain as influencer + reconcile\n"
        "/status — projects, stages, open tasks\n"
        "tasks — human queue, urgency-sorted, with digits\n"
        "decide <task_id> <digit> — present + decide (intent only, QP pending)\n"
        "receipt <id> — verify a receipt\n"
        "influencer <slug> — resources + stage\n"
        "products — product registry\n"
        "/help — this")


def _task_line(t: dict) -> str:
    u = t.get("urgency", {})
    opts = " ".join(f"[{k}]" for k in (t.get("options") or {}))
    return (f"· {t['id']} U={u.get('score', '?')} ({u.get('reason', '')})\n"
            f"  {t.get('title', '')} — {t.get('influencer', '')}/{t.get('resource_key', '')}\n"
            f"  {opts}")


def _decide(state: dict, task_id: str, digit: str, journal_path: str) -> dict:
    task = next((t for t in state.get("tasks", []) if t["id"] == task_id), None)
    if task is None:
        return {"reply": f"unknown task {task_id}. Say 'tasks' to see the queue."}
    if digit not in (task.get("options") or {}):
        return {"reply": f"digit {digit} not offered for {task_id}. Options: {list((task.get('options') or {}).keys())}"}
    from dash.hloop import HLoop
    from qp.journal import Journal
    try:
        ref = HLoop(journal_path).present(task)
        HLoop(journal_path).decide(task_id, ref)
    except (KeyError, ValueError) as e:
        return {"reply": f"hloop refused: {e}"}
    j = Journal(journal_path)
    idem = f"{task_id}:{digit}"
    cur = j.propose(idem, "task.decide")
    # Human approval authorizes intent only. Nothing executes: QP grant arrives later.
    if cur == "PROPOSED" and digit == "7":
        cur = j.transition(idem, "AUTHORIZED", note="human approved via chat, QP pending")
    status = "APPROVED_PENDING_QP" if cur == "AUTHORIZED" else "RECORDED"
    return {"reply": f"{task_id} digit {digit} → {status} (intent only, nothing executed).",
            "refresh": True}


def _receipt(rid: str) -> dict:
    sys.path.insert(0, PARENT)
    from dash.mcp import handle
    out = handle({}, "tools/call", {"name": "receipt.get", "arguments": {"id": rid}})
    if "error" in out:
        return {"reply": f"receipt {rid}: {out['error']}"}
    rc, v = out["result"]["receipt"], out["result"]["verify"]
    return {"reply": f"receipt {rc.get('id')} passed={rc.get('passed')} "
                     f"verify_ok={v.get('ok')} ({v.get('reason', '')})"}


def handle_chat(message: str, state: dict | None = None,
                journal_path: str | None = None) -> dict:
    parts = message.strip().split()
    if not parts:
        return {"reply": HELP}
    cmd = parts[0].lower()
    if cmd == "/help":
        return {"reply": HELP}
    if cmd == "/status":
        from dash.store import live_state
        try:
            d = live_state()
        except Exception:
            d = state or {"influencers": [], "tasks": []}
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

    st = state or {"influencers": [], "tasks": []}
    if cmd in ("tasks", "queue", "htasks"):
        tasks = st.get("tasks", [])
        if not tasks:
            return {"reply": "Queue empty. Clean."}
        return {"reply": "human queue, most urgent first:\n" +
                "\n".join(_task_line(t) for t in tasks[:15])}
    if cmd == "decide":
        if len(parts) != 3:
            return {"reply": "usage: decide <task_id> <digit> — e.g. decide T-001 7"}
        jp = journal_path or os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))
        return _decide(st, parts[1], parts[2], jp)
    if cmd == "receipt":
        if len(parts) != 2:
            return {"reply": "usage: receipt <receipt_id>"}
        return _receipt(parts[1])
    if cmd == "influencer":
        if len(parts) != 2:
            return {"reply": "usage: influencer <slug>"}
        inf = next((i for i in st.get("influencers", []) if i["slug"] == parts[1]), None)
        if not inf:
            return {"reply": f"unknown influencer {parts[1]}"}
        ready = sum(1 for r in inf["resources"] if r["status"] == "READY")
        lines = [f"{inf['name']} [{inf['stage']}] {ready}/{len(inf['resources'])} READY"]
        lines += [f"· {r['key']}: {r['status']} — {r.get('message', '')}"
                  for r in inf["resources"]]
        return {"reply": "\n".join(lines)}
    if cmd == "products":
        sys.path.insert(0, PARENT)
        from dash.mcp import PRODUCTS
        return {"reply": "products:\n" + "\n".join(
            f"· {p['name']} ({p['kind']}) — {p['intent']}" for p in PRODUCTS)}

    # Fallback: route by intent judges, confidence shown, never faked.
    try:
        sys.path.insert(0, PARENT)
        from qp.judges import intent_choice
        ic = intent_choice(message)
        hint = {"reply": "unknown command — I route by intent, I don't chat freely yet " +
                f"(intent={ic['choice']} conf={ic['confidence']}). Try: tasks, " +
                "decide <id> <digit>, receipt <id>, influencer <slug>, products, /status.",
                "intent": ic["choice"], "confidence": ic["confidence"]}
        if ic["choice"] in ("reply", "transact") and ic["confidence"] > 0.3 and st.get("tasks"):
            hint["reply"] += "\n\nMost urgent right now:\n" + _task_line(st["tasks"][0])
        return hint
    except Exception:
        return {"reply": f"unknown command. {HELP}"}
