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
        "check <name|domain> — check a name everywhere (RDAP, prices, handles)\n"
        "setup [slug] — provisioning pipeline: name→domain→email→phone→socials\n"
        "tasks — human queue, urgency-sorted, with digits\n"
        "decide <task_id> <digit> — present + decide (intent only, QP pending)\n"
        "receipt <id> — verify a receipt\n"
        "influencer <slug> — resources + stage\n"
        "products — product registry\n"
        "primitives <product> — exactly what it needs: objects, gates, grants, stubs\n"
        "/help — this")


def _check_name(arg: str) -> dict:
    from core.cmail.connectors.names import NamesConnector
    want_domain = "." in arg
    obs = NamesConnector().observe({"domain": arg} if want_domain else {"name": arg})
    lines = [f"{arg}: {obs.status} — {obs.message}"]
    if isinstance(obs.observed.get("prices"), dict):
        prices = obs.observed["prices"]
        items = prices if isinstance(prices, list) else prices.get("registrars", prices)
        try:
            lines.append("cheapest: " + ", ".join(
                f"{p.get('registrar', p.get('name', '?'))} {p.get('price', p.get('total', '?'))}"
                for p in (items if isinstance(items, list) else [])[:3]))
        except Exception:
            pass
    # handle namespace scan alongside (best effort, never blocking)
    name = arg.split(".")[0]
    try:
        import httpx
        from core.cmail.connectors.names import CHECKER
        from core.cmail.config import settings
        with httpx.Client(timeout=settings.http_timeout) as client:
            r = client.get(f"{CHECKER}/api/handles/{name}")
        if r.status_code == 200 and isinstance(r.json(), dict):
            body = r.json()
            lines.append(f"handles: {str(body)[:300]}")
    except Exception:
        lines.append("handles: UNKNOWN (scan unavailable)")
    if obs.status == "MISSING" and "buys" in obs.message:
        lines.append("next: human buys (docs/BUY-DOMAIN.md), then reconcile verifies + wires.")
    return {"reply": "\n".join(lines)}


PIPELINE = ["name", "handles", "names", "domain", "registrar", "zone",
            "mailbox", "number", "social:x", "content"]


def _setup(state: dict, slug: str | None) -> dict:
    infs = state.get("influencers", [])
    if slug:
        infs = [i for i in infs if i["slug"] == slug]
        if not infs:
            return {"reply": f"unknown influencer {slug}"}
    if not infs:
        return {"reply": "Nothing provisioning yet. /add <slug> <domain> starts the chain: "
                         "name → domain → email → phone → socials."}
    blocks = []
    for inf in infs:
        by_key = {r["key"]: r for r in inf["resources"]}
        rows = []
        for key in PIPELINE:
            r = by_key.get(key)
            if r is None:
                continue
            rows.append(f"{'●' if r['status'] == 'READY' else '○'} {key}: {r['status']}")
        ready = sum(1 for r in inf["resources"] if r["status"] == "READY")
        blocks.append(f"{inf['slug']} [{inf['stage']}] {ready}/{len(inf['resources'])} — "
                      "idea→endpoint:\n" + "\n".join(rows))
    return {"reply": "\n\n".join(blocks)}


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
    bare = cmd.strip("?!.,")
    if bare in ("help", "status"):
        return handle_chat("/" + bare, state=state, journal_path=journal_path)
    if bare in ("tasks", "queue", "htasks", "products"):
        cmd = bare  # fall through to the handlers below (no recursion)
    if bare == "setup" or cmd == "setup":
        slug = parts[1] if len(parts) > 1 else None
        return _setup(st, slug)
    if cmd == "check":
        if len(parts) != 2:
            return {"reply": "usage: check <name|domain> — e.g. check myname.dev"}
        return _check_name(parts[1].lower())
    if bare in ("hey", "hi", "hello", "yo", "sup", "morning", "evening", "howdy"):
        n_inf = len(st.get("influencers", []))
        n_tasks = len(st.get("tasks", []))
        top = f" Most urgent: {st['tasks'][0]['id']} — {st['tasks'][0].get('title', '')}" if n_tasks else ""
        return {"reply": f"hey. {n_inf} influencers, {n_tasks} open tasks.{top} "
                         "I can show tasks, decide, verify receipts, or brief an influencer. Try 'tasks'."}
    if bare in ("graph", "layers", "protocol", "qp"):
        sys.path.insert(0, PARENT)
        from dash.mcp import GRAPH
        return {"reply": "dependency graph:\n" + "\n".join(
            f"· {g['layer']}: {', '.join(g['functions'][:6])}"
            f"{'…' if len(g['functions']) > 6 else ''}" for g in GRAPH)}
    if bare in ("runs", "monitor", "activity"):
        runs = st.get("runs", [])
        if not runs:
            return {"reply": "No runs yet. Reconcile from the terminal rail or /add an influencer."}
        return {"reply": "latest runs:\n" + "\n".join(
            f"· {r['id']} {r.get('summary', '')} "
            f"{'[' + r['receipt_id'] + ']' if r.get('receipt_id') else '(no receipt)'}" for r in runs[:10])}
    if bare in ("agents", "trail", "predictions", "workers", "subagents"):
        jp = journal_path or os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))
        import sqlite3
        try:
            db = sqlite3.connect(jp)
            try:
                n = db.execute("SELECT COUNT(*), COALESCE(SUM(used),0) FROM predictions").fetchone()
                e = db.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
            except Exception:
                n, e = (0, 0), 0
            db.close()
            return {"reply": f"agent trail: {n[0]} presented, {n[1]} decided, {e} journal effects. "
                             "Worker/subagent spawn lands in Phase 3 — open the agents tab for the full ledger."}
        except Exception:
            return {"reply": "Agent trail empty — no predictions banked yet. Decide a task to start it."}
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
    if cmd == "modules":
        sys.path.insert(0, PARENT)
        from qp.modules import MODULES
        return {"reply": "modules (namespaces with teeth — receipts outside their "
                         "module's gates fail scope):\n" + "\n".join(
            f"· {m}: {s['description']} ({len(s['domains'])} claim domains)"
            for m, s in MODULES.items())}
    if cmd == "primitives":
        if len(parts) != 2:
            return {"reply": "usage: primitives <product> — e.g. primitives setup.social"}
        sys.path.insert(0, PARENT)
        from dash.mcp import handle as mcp_handle, _primitives
        prim = _primitives().get(parts[1])
        if not prim:
            return {"reply": f"unknown product {parts[1]}. Say 'products' for the list."}
        lines = [f"{prim['name']} ({prim['kind']}, {prim['status']}) — {prim['path']}",
                 f"module: {prim.get('module', '?')}",
                 f"objects: {', '.join(prim['objects'])}",
                 f"gates live: {', '.join(prim['gates_live'])}",
                 f"gates future: {', '.join(prim['gates_future']) or '—'}",
                 f"grants: {prim['grants']}", f"receipts: {prim['receipts']}",
                 f"proof level: {prim['proof_level']}",
                 f"live connectors: {', '.join(prim['connectors_live']) or '—'}",
                 f"stubs: {', '.join(prim['stubs']) or '—'}"]
        return {"reply": "\n".join(lines)}

    # Fallback: route by intent judges, confidence shown, never faked.
    try:
        sys.path.insert(0, PARENT)
        from qp.judges import intent_choice
        ic = intent_choice(message)
        hint = {"reply": "unknown command — I route by intent, I don't chat freely yet " +
                f"(intent={ic['choice']} conf={ic['confidence']}). Try: check <name>, setup, tasks, " +
                "decide <id> <digit>, receipt <id>, influencer <slug>, products, /status.",
                "intent": ic["choice"], "confidence": ic["confidence"]}
        if ic["choice"] in ("reply", "transact") and ic["confidence"] > 0.3 and st.get("tasks"):
            hint["reply"] += "\n\nMost urgent right now:\n" + _task_line(st["tasks"][0])
        return hint
    except Exception:
        return {"reply": f"unknown command. {HELP}"}
