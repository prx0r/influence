"""Influence dash server. Stdlib only. Serves static HTML + JSON state.

Routes: health/state (seed LIVE=0 or SQLite reconcile LIVE=1), chat
(agent loop over the graph), vault, reconcile, present/decide (HLoop +
journal), MCP (read-only tools). Binds 127.0.0.1 only — public access is
the Cloudflare tunnel. DASH_TOKEN empty = open (normal for tunnel-only
ops). If DASH_TOKEN is set, ?token= or Cookie: dash_auth=<token> works;
a valid ?token= also sets the cookie so you don't paste it every time."""
from __future__ import annotations

import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

_SNAP: dict = {}

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
SEED = os.path.join(ROOT, "seed.json")
PORT = int(os.environ.get("DASH_PORT", "8793"))
LIVE = os.environ.get("LIVE", "0") == "1"
# Empty = open (loopback + tunnel). Set only if you want an extra app-level gate.
TOKEN = os.environ.get("DASH_TOKEN", "").strip()


def _urgency_of(task: dict) -> dict:
    """Urgency for the human rail. Rule-based v0 (qp/judges): scored from
    title+instructions, blended with the task's risk. Falls back to risk
    alone if judges are unavailable — never a fake precision."""
    text = f"{task.get('title', '')}\n{task.get('instructions', '')}"
    risk = float(task.get("risk", 0.3) or 0.0)
    try:
        sys.path.insert(0, os.path.dirname(ROOT))
        from qp.judges import urgency_score
        u = urgency_score(text)
        score = round(min(2.0, u["score"] + risk), 3)
        return {"score": score, "confidence": u["confidence"],
                "reason": f"urgency={u['score']} risk={risk}"}
    except Exception:
        return {"score": round(risk, 3), "confidence": 0.0,
                "reason": f"risk={risk} (judges unavailable)"}


_STATE_CACHE: dict = {"at": 0.0, "state": None}
STATE_TTL = 20.0
_STORE_LOCK = None


def _store_lock():
    global _STORE_LOCK
    if _STORE_LOCK is None:
        import threading
        _STORE_LOCK = threading.Lock()
    return _STORE_LOCK


def load_state() -> dict:
    import time as _t
    now = _t.time()
    if _STATE_CACHE.get("state") is not None and now - _STATE_CACHE.get("at", 0) < STATE_TTL:
        return _STATE_CACHE["state"]
    if LIVE:
        sys.path.insert(0, os.path.dirname(ROOT))
        from dash.store import live_state
        with _store_lock():
            d = live_state()
    else:
        with open(SEED) as f:
            d = json.load(f)
    tasks = d.get("tasks", [])
    for t in tasks:
        t["urgency"] = _urgency_of(t)
    tasks.sort(key=lambda t: (-t["urgency"]["score"], t.get("id", "")))
    d["tasks"] = tasks
    _STATE_CACHE["state"] = d
    _STATE_CACHE["at"] = now
    try:
        import sqlite3 as _sq
        _c = _sq.connect(os.getenv("DASH_DB", os.path.join(ROOT, "influence.db")), timeout=5)
        _c.execute("DELETE FROM run_logs WHERE id NOT IN (SELECT id FROM run_logs ORDER BY id DESC LIMIT 600)")
        _c.commit()
        _c.close()
    except Exception:
        pass
    return d


REPO_ROOT = os.path.dirname(ROOT)
FILES_ALLOW = {".py", ".md", ".json", ".txt", ".sh", ".html", ".toml", ".yml", ".yaml", ".ts"}
FILES_DENY = {".token", "vault.json", "decisions.db", "influence.db", "receipts.jsonl",
              ".env", "vault.key", "tunnel.log", "dash.log"}


def read_repo_file(path: str) -> dict:
    """Read-only repo browser for the IDE tab. Secrets and DBs never serve."""
    if not path or path.startswith("/") or ".." in path.split("/"):
        if path not in ("", "/"):
            return {"error": "bad path"}
        path = ""
    full = os.path.realpath(os.path.join(REPO_ROOT, path))
    if not full.startswith(os.path.realpath(REPO_ROOT) + os.sep) and full != os.path.realpath(REPO_ROOT):
        return {"error": "outside repo"}
    if os.path.isdir(full):
        try:
            entries = sorted(os.listdir(full))
        except OSError as e:
            return {"error": str(e)[:120]}
        out = []
        for name in entries:
            if name.startswith(".") or name == "__pycache__":
                continue
            p = os.path.join(full, name)
            rel = os.path.relpath(p, REPO_ROOT)
            if os.path.basename(name) in FILES_DENY:
                continue
            out.append({"name": name, "path": rel,
                        "dir": os.path.isdir(p),
                        "size": 0 if os.path.isdir(p) else os.path.getsize(p)})
        return {"dir": path or "/", "entries": out[:200]}
    base = os.path.basename(full)
    if base in FILES_DENY or os.path.splitext(base)[1] not in FILES_ALLOW:
        return {"error": "not servable"}
    try:
        if os.path.getsize(full) > 200_000:
            return {"error": "too large"}
        with open(full, encoding="utf-8", errors="replace") as f:
            return {"path": path, "content": f.read()}
    except OSError as e:
        return {"error": str(e)[:120]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STATIC, **kw)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self) -> tuple[bool, bool]:
        """Return (ok, set_cookie). Cookie is set only when a valid ?token= is used."""
        if not TOKEN:
            return True, False
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        qt = q.get("token", [""])[0]
        if qt and qt == TOKEN:
            return True, True
        cookies = {}
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()
        if cookies.get("dash_auth") == TOKEN:
            return True, False
        return False, False

    def _route(self) -> str:
        return urlparse(self.path).path

    def _auth_gate(self) -> bool:
        ok, set_cookie = self._authed()
        if not ok:
            self._json({"error": "forbidden"}, 403)
            return False
        self._want_cookie = set_cookie
        return True

    def end_headers(self):
        if getattr(self, "_want_cookie", False) and TOKEN:
            self.send_header(
                "Set-Cookie",
                f"dash_auth={TOKEN}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000",
            )
            self._want_cookie = False
        if urlparse(self.path).path in ("/", "/index.html"):
            self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        if self._route() == "/api/health":
            return self._json({"ok": True, "dash": "influence"})
        if self._route() == "/api/brand-logo":
            if not self._auth_gate():
                return
            from urllib.parse import parse_qs as _pq, urlparse as _up
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.brand_logo import logo_svg, spinner_svg
            q = _pq(_up(self.path).query)
            slug = (q.get("slug") or ["oddhobb"])[0]
            size = int((q.get("size") or ["64"])[0][:3] or 64)
            svg = spinner_svg(slug, size) if "spin" in q else logo_svg(slug, size)
            body = svg.encode()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)
            return
        if not self._auth_gate():
            return
        if self._route() == "/api/vault":
            sys.path.insert(0, os.path.dirname(ROOT))
            from core.vault.store import Vault
            vroot = os.path.dirname(ROOT)
            v = Vault(os.getenv("INFLUENCE_VAULT", os.path.join(vroot, "dash", "vault.json")))
            keys = v.find(active_only=False)
            for k in keys:
                k.pop("capability", None)  # capabilities never leave the server
            return self._json({"keys": keys})
        if self._route() == "/api/state":
            try:
                st = load_state()
                _SNAP["state"] = st
                import time as _t
                _SNAP["at"] = _t.time()
                return self._json(st)
            except Exception as e:
                if _SNAP.get("state"):
                    cached = dict(_SNAP["state"])
                    cached["stale"] = True
                    return self._json(cached)
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/files":
            return self._json(read_repo_file(parse_qs(urlparse(self.path).query).get("path", [""])[0]))
        if self._route() == "/api/studio/art":
            sys.path.insert(0, ROOT)
            from sleep_studio import list_art
            try:
                return self._json({"art": list_art()})
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/studio/job":
            sys.path.insert(0, ROOT)
            from sleep_studio import job_status
            jid = parse_qs(urlparse(self.path).query).get("jid", [""])[0]
            return self._json(job_status(jid))
        if self._route() == "/api/studio/file":
            sys.path.insert(0, ROOT)
            import sleep_studio as _st
            q = parse_qs(urlparse(self.path).query)
            kind = q.get("kind", [""])[0]
            if kind == "art":
                base = os.path.basename(q.get("file", [""])[0])
                full = os.path.realpath(os.path.join(_st.ART, base))
                root = os.path.realpath(_st.ART)
                ctype, ok = "image/jpeg", base.endswith(".jpg")
            elif kind == "rend":
                d = os.path.basename(q.get("dir", [""])[0])
                base = os.path.basename(q.get("file", [""])[0])
                full = os.path.realpath(os.path.join(_st.REND, d, base))
                root = os.path.realpath(_st.REND)
                ctype = ("video/mp4" if base.endswith(".mp4")
                         else "image/jpeg" if base.endswith(".jpg") else "")
                ok = bool(ctype)
            elif kind == "voice":
                base = os.path.basename(q.get("file", [""])[0])
                full = os.path.realpath(os.path.join(_st.VOICE, base))
                root = os.path.realpath(_st.VOICE)
                ctype, ok = "audio/mpeg", base.endswith(".mp3")
            else:
                return self._json({"error": "kind?"}, 400)
            if not ok or not full.startswith(root + os.sep):
                return self._json({"error": "bad file"}, 400)
            try:
                body = open(full, "rb").read()
            except OSError:
                return self._json({"error": "missing"}, 404)
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if self._route() == "/api/onboarding":
            # Brand-agnostic social claim kit — same registry as passport + chat.
            from urllib.parse import parse_qs as _pq, urlparse as _up
            q = _pq(_up(self.path).query)
            slug = (q.get("slug") or [""])[0]
            handle = (q.get("handle") or [""])[0]
            domain = (q.get("domain") or [""])[0]
            sys.path.insert(0, os.path.dirname(ROOT))
            from core.cmail.social_onboarding import format_onboarding_reply, render_brand_onboarding
            brand: dict = {}
            if slug:
                try:
                    st = load_state()
                except Exception as e:
                    return self._json({"error": str(e)[:200]}, 500)
                inf = next((i for i in st.get("influencers", []) if i["slug"] == slug), None)
                if not inf:
                    return self._json({"error": f"unknown influencer {slug}"}, 404)
                handle = handle or (inf.get("handle") or inf.get("slug", "")).replace("@", "").replace("-", "")
                domain = domain or inf.get("domain") or ""
                brand["display_name"] = inf.get("name") or handle.title()
                for r in inf.get("resources", []):
                    d = r.get("desired") or {}
                    if r.get("key") == "domain" and d.get("domain"):
                        domain = domain or d["domain"]
                    kit = r.get("kit") or d.get("kit") or {}
                    for bk in ("phone", "email", "website"):
                        if kit.get(bk) and not brand.get(bk):
                            brand[bk] = kit[bk]
                if not domain and "." in str(inf.get("slug", "")):
                    domain = str(inf["slug"])
            if not handle:
                return self._json({"error": "slug or handle required"}, 400)
            if not domain:
                domain = f"{handle.lower()}.com"
            try:
                on = render_brand_onboarding(handle, domain, brand=brand)
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
            return self._json({"ok": True, "onboarding": on, "text": format_onboarding_reply(on)})
        if self._route() == "/api/notifications":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from dash.notifications import notifications
                q = parse_qs(urlparse(self.path).query)
                try:
                    limit = int(str((q.get("limit") or ["40"])[0]).split("?")[0] or 40)
                except ValueError:
                    limit = 40
                limit = max(5, min(limit, 100))
                return self._json(notifications(limit=limit))
            except Exception as e:
                return self._json({"error": str(e)[:200], "items": [], "counts": {}}, 500)
        if self._route() == "/api/agent-feed":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from dash.notifications import agent_feed
                q = parse_qs(urlparse(self.path).query)
                try:
                    limit = int(str((q.get("limit") or ["40"])[0]).split("?")[0] or 40)
                except ValueError:
                    limit = 40
                limit = max(5, min(limit, 100))
                return self._json(agent_feed(limit=limit))
            except Exception as e:
                return self._json({"error": str(e)[:200], "items": [], "counts": {}}, 500)
        if self._route() == "/api/actions":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.actions import list_actions, totals
                q = parse_qs(urlparse(self.path).query)
                channel = (q.get("channel") or [None])[0]
                campaign = (q.get("campaign") or [None])[0]
                status = (q.get("status") or [None])[0]
                try:
                    limit = int(str((q.get("limit") or ["50"])[0]).split("?")[0] or 50)
                except ValueError:
                    limit = 50
                limit = max(1, min(limit, 200))
                return self._json({
                    "actions": list_actions(channel, campaign, status, limit),
                    "totals": totals(campaign),
                })
            except Exception as e:
                return self._json({"error": str(e)[:200], "actions": [], "totals": {}}, 500)
        if self._route() == "/api/suppliers":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.suppliers import list_suppliers, quiet
                q = parse_qs(urlparse(self.path).query)
                status = (q.get("status") or [None])[0]
                return self._json({
                    "suppliers": list_suppliers(status),
                    "chase": quiet(),
                })
            except Exception as e:
                return self._json({"error": str(e)[:200], "suppliers": []}, 500)
        if self._route() == "/api/supplier-thread":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.suppliers import thread, latest
                q = parse_qs(urlparse(self.path).query)
                slug = (q.get("slug") or [""])[0]
                if not slug:
                    return self._json({"error": "slug required"}, 400)
                return self._json({
                    "thread": thread(slug),
                    "latest": latest(slug),
                })
            except KeyError as e:
                return self._json({"error": str(e)[:160]}, 404)
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/accounts":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.channel_state import list_accounts, can_publish
                q = parse_qs(urlparse(self.path).query)
                brand = (q.get("brand") or [None])[0]
                return self._json({"accounts": list_accounts(brand)})
            except Exception as e:
                return self._json({"error": str(e)[:200], "accounts": []}, 500)
        if self._route() == "/api/campaigns":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.campaign import list_campaigns, get_campaign
                q = parse_qs(urlparse(self.path).query)
                cid = (q.get("id") or [None])[0]
                brand = (q.get("brand") or [None])[0]
                if cid:
                    c = get_campaign(int(cid))
                    return self._json({"campaign": c} if c else {"error": "not found"}, 200 if c else 404)
                return self._json({"campaigns": list_campaigns(brand)})
            except Exception as e:
                return self._json({"error": str(e)[:200], "campaigns": []}, 500)
        if self._route() == "/api/goals":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.goals import list_goals, goal_status
                q = parse_qs(urlparse(self.path).query)
                gid = (q.get("id") or [None])[0]
                entity = (q.get("entity") or [None])[0]
                if gid:
                    return self._json({"goal": goal_status(int(gid))})
                return self._json({"goals": list_goals(entity)})
            except Exception as e:
                return self._json({"error": str(e)[:200], "goals": []}, 500)
        if self._route() == "/api/packs":
            # Catalog packs (canonical). ?legacy=1 for old oddhobbies packs.
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                q = parse_qs(urlparse(self.path).query)
                if (q.get("legacy") or [""])[0] == "1":
                    from pipeline.compilers.pack_loader import list_packs
                    store = (q.get("store") or ["oddhobb"])[0]
                    return self._json({"packs": list_packs(store), "source": "legacy"})
                from pipeline.catalog import list_packs
                level = (q.get("level") or [None])[0]
                return self._json({"packs": list_packs(level), "source": "catalog"})
            except Exception as e:
                return self._json({"error": str(e)[:200], "packs": []}, 500)
        if self._route() == "/api/compile":
            # Pure dry-run preview: zero DB writes. Use POST /api/release/create
            # to draft a release + bundle + task.
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.runner import preview_pack
                q = parse_qs(urlparse(self.path).query)
                sku = (q.get("sku") or [""])[0]
                if not sku:
                    return self._json({"error": "sku required"}, 400)
                return self._json(preview_pack(
                    sku,
                    (q.get("brand") or ["oddhobb"])[0],
                    (q.get("channel") or ["etsy"])[0]))
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/etsy-listing":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline import etsy_listing as _el
                q = parse_qs(urlparse(self.path).query)
                sku = (q.get("sku") or [""])[0]
                store = (q.get("store") or ["oddhobb"])[0]
                if not sku:
                    return self._json({"error": "sku required"}, 400)
                return self._json(_el.preview(store, sku))
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/review/bundle":
            # Universal Review Canvas data (dirs 19-25): one endpoint renders
            # whatever the active Human Task reviews. APPROVE/CHANGE/REJECT.
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.effects import get_bundle, get_task
                q = parse_qs(urlparse(self.path).query)
                bid = (q.get("id") or [""])[0]
                if not bid:
                    return self._json({"error": "id required"}, 400)
                b = get_bundle(bid)
                if not b:
                    return self._json({"error": "unknown bundle"}, 404)
                return self._json({"bundle": b})
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/review/queue":
            # What needs judgment, ranked (dir 37)
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.effects import queue
                q = parse_qs(urlparse(self.path).query)
                brand = (q.get("brand") or [None])[0]
                return self._json({"queue": queue(brand)})
            except Exception as e:
                return self._json({"error": str(e)[:200], "queue": []}, 500)
        if self._route() == "/api/task/status":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.effects import get_task
                q = parse_qs(urlparse(self.path).query)
                tid = (q.get("task_id") or [""])[0]
                if not tid:
                    return self._json({"error": "task_id required"}, 400)
                t = get_task(int(tid))
                if not t:
                    return self._json({"error": "unknown task"}, 404)
                return self._json({"task_id": t["id"], "state": t["state"],
                                   "brand": t["brand"], "kind": t["kind"],
                                   "payload_hash": t["payload_hash"][:16] if t.get("payload_hash") else None,
                                   "receipt_id": t.get("receipt_id"),
                                   "decision": t.get("decision"),
                                   "risk_class": t.get("risk_class")})
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/actions-totals":
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.actions import totals
                q = parse_qs(urlparse(self.path).query)
                campaign = (q.get("campaign") or [None])[0]
                return self._json(totals(campaign))
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/agents":
            # HLoop present→decide trail + journal effect states. This is the
            # agent-activity ledger the Agents tab renders. Worker/subagent
            # spawn arrives in Phase 3; until then this trail is the truth.
            import sqlite3
            journal_path = os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))
            out = {"predictions": [], "effects": [],
                   "counts": {"presented": 0, "decided": 0, "effects": 0}}
            try:
                db = sqlite3.connect(journal_path)
                try:
                    rows = db.execute("SELECT ref, task_id, at, used FROM predictions "
                                      "ORDER BY at DESC LIMIT 20").fetchall()
                    out["predictions"] = [{"ref": r[0], "task": r[1], "at": r[2],
                                           "used": bool(r[3])} for r in rows]
                    n = db.execute("SELECT COUNT(*), SUM(used) FROM predictions").fetchone()
                    out["counts"]["presented"], out["counts"]["decided"] = n[0] or 0, n[1] or 0
                except Exception:
                    pass
                try:
                    rows = db.execute("SELECT idem, action, state FROM effects "
                                      "ORDER BY updated_at DESC LIMIT 20").fetchall()
                    out["effects"] = [{"idem": r[0], "action": r[1], "state": r[2]}
                                      for r in rows]
                    out["counts"]["effects"] = db.execute(
                        "SELECT COUNT(*) FROM effects").fetchone()[0]
                except Exception:
                    pass
                db.close()
            except Exception:
                pass
            return self._json(out)
        if self._route() == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if not self._authed():
            return self._json({"error": "forbidden"}, 403)
        if self._route() == "/api/release/create":
            # Draft release + ReviewBundle + effect task. Never pushes.
            # Publishing is: approve task → runtime.execute → adapter → verify.
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.runner import run_pack
                sku = str(body.get("sku") or "")
                if not sku:
                    return self._json({"error": "sku required"}, 400)
                out = run_pack(sku, str(body.get("brand") or "oddhobb"),
                               str(body.get("channel") or "etsy"),
                               body.get("campaign"))
                return self._json(out)
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/review/decide":
            # APPROVE / REJECT / CHANGE on an effect task. (dirs 15-17, 23)
            # APPROVE binds the frozen payload hash — never prose.
            # CHANGE creates a new bundle revision (approval never transfers).
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            try:
                sys.path.insert(0, os.path.dirname(ROOT))
                from pipeline.effects import transition, get_task, create_bundle
                tid = int(body.get("task_id", 0))
                decision = str(body.get("decision", "")).upper()
                if decision == "APPROVE":
                    t = get_task(tid)
                    if not t:
                        return self._json({"error": "unknown task"}, 404)
                    if t["state"] != "REVIEW_READY":
                        return self._json({"error": f"task is {t['state']}, not REVIEW_READY"}, 409)
                    transition(tid, "APPROVED", by=str(body.get("by", "owner")))
                    return self._json({"ok": True, "task_id": tid, "state": "APPROVED",
                                       "payload_hash": t["payload_hash"]})
                if decision == "REJECT":
                    transition(tid, "REJECTED", by=str(body.get("by", "owner")))
                    return self._json({"ok": True, "task_id": tid, "state": "REJECTED"})
                if decision == "CHANGE":
                    # new revision: recompile handled by caller, which passes new payload
                    t = get_task(tid)
                    if not t:
                        return self._json({"error": "unknown task"}, 404)
                    return self._json({"ok": True, "task_id": tid,
                                       "next": "submit revised payload via /api/review/revise"})
                return self._json({"error": "decision must be APPROVE, REJECT, or CHANGE"}, 400)
            except (KeyError, ValueError) as e:
                return self._json({"error": str(e)[:200]}, 409)
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route().startswith("/api/studio/"):
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            sys.path.insert(0, ROOT)
            try:
                import sleep_studio as _st
                if self._route() == "/api/studio/generate":
                    return self._json({"ok": True, **_st.generate(
                        str(body.get("prompt", "")),
                        str(body.get("style", "pencil") or "pencil"),
                        str(body.get("model", "flux") or "flux"))})
                if self._route() == "/api/studio/narrate":
                    return self._json({"ok": True, **_st.narrate(
                        str(body.get("text", "")),
                        str(body.get("voice", "aria") or "aria"),
                        str(body.get("rate", "-5%") or "-5%"),
                        str(body.get("pitch", "-2Hz") or "-2Hz"))})
                if self._route() == "/api/studio/render":
                    knobs = dict(body.get("knobs", {}))
                    knobs["dur"] = int(knobs.get("dur", 30000))
                    return self._json({"ok": True, "jid": _st.start_render(
                        str(body.get("name", "")), knobs)})
                if self._route() == "/api/studio/publish":
                    job = _st.JOBS.get(str(body.get("jid", "")))
                    if not job or job.get("status") != "done":
                        return self._json({"error": "render not done"}, 409)
                    return self._json({"ok": True, **_st.publish(
                        job["mp4path"],
                        str(body.get("title", "sleep-test")),
                        {"name": job.get("name"), "knobs": job.get("knobs")})})
            except Exception as e:
                return self._json({"error": str(e)[:300]}, 500)
            return self._json({"error": "not found"}, 404)
        if not self._auth_gate():
            return
        if self._route() == "/api/chat":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.chat import handle_chat
            try:
                state = load_state()
            except Exception:
                state = None
            journal_path = os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))
            try:
                return self._json(handle_chat(str(body.get("message", "")),
                                              state=state, journal_path=journal_path,
                                              brand=str(body.get("brand", "") or ""),
                                              history=body.get("history") or []))
            except Exception as e:
                return self._json({"reply": f"error: {str(e)[:200]}"})
        if self._route() == "/api/vault-store":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            value = str(body.get("value", ""))
            name = str(body.get("name", "")).strip()
            if not value or not name:
                return self._json({"ok": False, "error": "name + value required"}, 400)
            sys.path.insert(0, os.path.dirname(ROOT))
            from core.vault.store import Vault
            v = Vault(os.getenv("INFLUENCE_VAULT", os.path.join(os.path.dirname(ROOT), "dash", "vault.json")))
            out = v.store(name, value, ["influence-dash"], ["operator"],
                          kind=str(body.get("kind", "other")))
            return self._json({"ok": True, **out})
        if self._route() == "/api/reconcile":
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.store import live_state
            try:
                with _store_lock():
                    d = live_state()
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
            return self._json({"ok": True, "projects": len(d["influencers"]),
                               "tasks": len(d["tasks"])})
        if self._route() == "/api/resource-done":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            slug, key = str(body.get("slug", "")), str(body.get("resource_key", ""))
            done = body.get("done", True)
            if not slug or not key:
                return self._json({"error": "slug + resource_key required"}, 400)
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.store import mark_resource_done
            db_path = os.getenv("DASH_DB", os.path.join(ROOT, "influence.db"))
            try:
                return self._json({"ok": True,
                                   **mark_resource_done(slug, key, bool(done), db_path)})
            except KeyError as e:
                return self._json({"error": str(e)[:160]}, 404)
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/task-start":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            tid = str(body.get("task_id", ""))
            if not tid:
                return self._json({"error": "task_id required"}, 400)
            try:
                st = load_state()
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
            t = next((x for x in st.get("tasks", []) if x.get("id") == tid), None)
            if not t:
                return self._json({"error": f"unknown task {tid}"}, 404)
            slug = t.get("influencer", "")
            vname = re.sub(r"[^A-Z0-9]+", "_", f"{slug}_{t.get('resource_key', 'secret')}".upper()).strip("_")[:48]
            secretish = bool(re.search(r"secret|key|token|password|bearer|credential|api",
                                        f"{t.get('title', '')} {t.get('instructions', '')}", re.I))
            links = []
            if t.get("url"):
                links.append({"label": "Open", "url": t["url"]})
            links.append({"label": "Claim kit", "url": f"/api/onboarding?slug={slug}"})
            guide = [f"Task {tid}: {t.get('title', '')}", "",
                     (t.get("instructions", "") or "").strip()]
            if t.get("url"):
                guide += ["", f"Link: {t['url']}"]
            if secretish:
                guide += ["", f"Vault name: {vname} (editable in the rail box below)",
                          "Paste the value into the vault box — never into chat."]
            guide += ["", f"Reply DONE or press ✓ when finished."]
            return self._json({"ok": True, "task_id": tid, "slug": slug,
                               "guide": "\n".join(guide), "links": links,
                               "vault_name": vname if secretish else "",
                               "walk_prompt": f"Walk me through task {tid} ({t.get('title', '')}) for {slug} step by step."})
        if self._route() == "/api/autopilot":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.store import autopilot_run
            db_path = os.getenv("DASH_DB", os.path.join(ROOT, "influence.db"))
            try:
                out = autopilot_run(str(body.get("slug") or "") or None, db_path)
                return self._json({"ok": True, **out})
            except KeyError as e:
                return self._json({"error": str(e)[:160]}, 404)
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/present":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            task_id = str(body.get("task_id", ""))
            try:
                state = load_state()
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
            task = next((t for t in state.get("tasks", []) if t["id"] == task_id), None)
            if task is None:
                return self._json({"error": "unknown task"}, 404)
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.hloop import HLoop
            ref = HLoop(os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))).present(task)
            return self._json({"ok": True, "prediction_ref": ref})
        if self._route() == "/mcp":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.mcp import handle
            try:
                state = load_state()
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
            return self._json(handle(state, body.get("method", ""),
                                     body.get("params", {})))
        if self._route() != "/api/decide":
            return self._json({"error": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)
        task_id, digit = str(body.get("task_id", "")), str(body.get("digit", ""))
        prediction_ref = str(body.get("prediction_ref", ""))
        try:
            state = load_state()
        except Exception as e:
            return self._json({"error": str(e)[:200]}, 500)
        task = next((t for t in state.get("tasks", []) if t["id"] == task_id), None)
        if task is None:
            return self._json({"error": "unknown task"}, 404)
        if digit not in task.get("options", {}):
            return self._json({"error": "digit not offered"}, 400)
        sys.path.insert(0, os.path.dirname(ROOT))
        from dash.hloop import HLoop
        from qp.journal import Journal
        journal_path = os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))
        try:
            HLoop(journal_path).decide(task_id, prediction_ref)
        except KeyError:
            return self._json({"error": "present the task first (no banked prediction)"}, 409)
        except ValueError as e:
            return self._json({"error": str(e)[:120]}, 409)
        j = Journal(journal_path)
        idem = f"{task_id}:{digit}"
        cur = j.propose(idem, "task.decide")
        # Human approval authorizes intent only. Nothing executes: QP grant arrives in phase 3.
        if cur == "PROPOSED" and digit == "7":
            cur = j.transition(idem, "AUTHORIZED", note="human approved, QP pending")
        status = "APPROVED_PENDING_QP" if cur == "AUTHORIZED" else "RECORDED"
        return self._json({"ok": True, "task": task_id, "digit": digit, "state": status})


def main():
    for _db in (os.getenv("DASH_DB", os.path.join(ROOT, "influence.db")),
                os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))):
        try:
            import sqlite3
            c = sqlite3.connect(_db, timeout=30)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=10000")
            c.commit()
            c.close()
        except Exception:
            pass
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"influence step-0 dash on http://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
