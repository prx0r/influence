"""Influence dash server. Stdlib only. Serves static HTML + JSON state.

Routes: health/state (seed LIVE=0 or SQLite reconcile LIVE=1), chat,
vault, reconcile, present/decide (HLoop + journal), verify (QP chain),
resource-done (close static checklists), autopilot (conservative AUTO
loop), MCP (read-only tools). Binds loopback; token-gated when set."""
from __future__ import annotations

import json
import os
import secrets
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
SEED = os.path.join(ROOT, "seed.json")
PORT = int(os.environ.get("DASH_PORT", "8793"))
LIVE = os.environ.get("LIVE", "0") == "1"
TOKEN = os.environ.get("DASH_TOKEN", "")  # empty = loopback dev only; set before any tunnel


def load_state() -> dict:
    if LIVE:
        sys.path.insert(0, os.path.dirname(ROOT))
        from dash.store import live_state
        return live_state()
    with open(SEED) as f:
        return json.load(f)


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

    def _authed(self) -> bool:
        if not TOKEN:
            return True  # dev loopback: server binds 127.0.0.1 only
        q = parse_qs(urlparse(self.path).query)
        return q.get("token", [""])[0] == TOKEN

    def _route(self) -> str:
        return urlparse(self.path).path

    def do_GET(self):
        if self._route() == "/api/health":
            return self._json({"ok": True, "dash": "influence"})
        if not self._authed():
            return self._json({"error": "forbidden"}, 403)
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
                return self._json(load_state())
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
        if self._route() == "/api/files":
            return self._json(read_repo_file(parse_qs(urlparse(self.path).query).get("path", [""])[0]))
        if self._route() == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if not self._authed():
            return self._json({"error": "forbidden"}, 403)
        if self._route() == "/api/chat":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            sys.path.insert(0, os.path.dirname(ROOT))
            from dash.chat import handle_chat
            try:
                return self._json(handle_chat(str(body.get("message", ""))))
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
                d = live_state()
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 500)
            return self._json({"ok": True, "projects": len(d["influencers"]),
                               "tasks": len(d["tasks"])})
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
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"influence step-0 dash on http://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
