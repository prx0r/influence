"""Step-0 dash tests. Stdlib only: boots server, checks health + state shape, scans for leaked secrets."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = "8794"
SECRET_RE = re.compile(r"(ghp_|cfat_|cfut_|sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16})")


def get(path, port=PORT):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as r:
        return r.status, r.read()


def post(port, path, obj):
    import json as _json
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                 data=_json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def check_state_shape(d):
    assert "influencers" in d and "tasks" in d and "runs" in d, "state keys"
    for i in d["influencers"]:
        assert i["slug"] and i["resources"], f"influencer shape {i}"
        for r in i["resources"]:
            assert r["key"] and r["kind"] and r["status"] in (
                "READY", "MISSING", "BLOCKED", "UNKNOWN", "ERROR"), f"resource {r}"
    keys = {(i["slug"], r["key"]) for i in d["influencers"] for r in i["resources"]}
    for t in d["tasks"]:
        assert (t["influencer"], t["resource_key"]) in keys, f"task maps {t['id']}"


def main():
    env = dict(os.environ, DASH_PORT=PORT, DASH_TOKEN="",
               DASH_JOURNAL="/tmp/dash-journal-test.db",
               INFLUENCE_VAULT="/tmp/dash-vault-test.json")
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "server.py")], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try:
                status, body = get("/api/health")
                if status == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            print("FAIL: server did not boot")
            return 1
        status, body = get("/api/health")
        assert status == 200 and json.loads(body)["ok"] is True, "health"
        status, body = get("/api/state")
        assert status == 200, "state status"
        d = json.loads(body)
        check_state_shape(d)
        assert not SECRET_RE.search(body.decode()), "no secrets in state"
        status, body = get("/")
        assert status == 200 and b"influence" in body, "index serves"
        # decide path: unknown task 404, bad digit 400, approve recorded + idempotent
        status, _ = post(PORT, "/api/decide", {"task_id": "NOPE", "digit": "7"})
        assert status == 404, "unknown task"
        status, body = get("/api/state")
        first = json.loads(body)["tasks"][0]
        status, _ = post(PORT, "/api/decide", {"task_id": first["id"], "digit": "99"})
        assert status == 400, "bad digit"
        status, body = post(PORT, "/api/decide", {"task_id": first["id"], "digit": "7"})
        assert status == 409, "decide without present rejected"
        status, body = post(PORT, "/api/present", {"task_id": first["id"]})
        assert status == 200 and json.loads(body)["prediction_ref"], "present banks"
        ref = json.loads(body)["prediction_ref"]
        status, body = post(PORT, "/api/decide", {"task_id": first["id"], "digit": "7",
                                                  "prediction_ref": ref})
        assert status == 200 and json.loads(body)["state"] == "APPROVED_PENDING_QP", "approve"
        status, _ = post(PORT, "/api/decide", {"task_id": first["id"], "digit": "7",
                                               "prediction_ref": ref})
        assert status == 409, "prediction single-use"
        # mcp: list + call + unknown tool, read-only surface matches state
        status, body = post(PORT, "/mcp", {"method": "tools/list", "params": {}})
        assert status == 200, "mcp list"
        names = {t["name"] for t in json.loads(body)["tools"]}
        assert names == {"influencer.list", "influencer.get", "queue.list",
                         "graph.describe", "product.list", "product.get",
                         "receipt.get"}, "mcp tools"
        slug = json.loads(get("/api/state")[1])["influencers"][0]["slug"]
        status, body = post(PORT, "/mcp", {"method": "tools/call",
                                           "params": {"name": "influencer.get", "arguments": {"slug": slug}}})
        assert status == 200 and json.loads(body)["result"]["slug"] == slug, "mcp get"
        status, body = post(PORT, "/mcp", {"method": "tools/call",
                                           "params": {"name": "nope", "arguments": {}}})
        assert status == 200 and "error" in json.loads(body), "mcp unknown tool"
        status, body = post(PORT, "/mcp", {"method": "tools/call",
                                           "params": {"name": "graph.describe", "arguments": {}}})
        layers = [g["layer"] for g in json.loads(body)["result"]]
        assert layers[0].startswith("L0") and layers[-1].startswith("L7"), "graph flow"
        status, body = post(PORT, "/mcp", {"method": "tools/call",
                                           "params": {"name": "product.get", "arguments": {"name": "funnylab"}}})
        assert json.loads(body)["result"]["kind"] == "infra", "product get"
        status, body = post(PORT, "/mcp", {"method": "tools/call",
                                           "params": {"name": "product.get", "arguments": {"name": "nope"}}})
        assert "error" in json.loads(body), "product unknown"
        status, body = post(PORT, "/mcp", {"method": "tools/call",
                                           "params": {"name": "receipt.get", "arguments": {"id": "receipt:nope"}}})
        assert "error" in json.loads(body), "receipt unknown"
        # files: dir listing, file read, secrets denied
        status, body = get("/api/files?path=products")
        assert status == 200 and any(e["name"] == "funnylab.md"
                                     for e in json.loads(body)["entries"]), "files dir"
        status, body = get("/api/files?path=products/funnylab.md")
        assert status == 200 and "funnylab" in json.loads(body)["content"], "files read"
        status, body = get("/api/files?path=dash/.token")
        assert "error" in json.loads(body), "token denied"
        status, body = get("/api/files?path=../qpbot")
        assert "error" in json.loads(body), "escape denied"
        # chat: help + unknown; vault: deposit then list (metadata only)
        status, body = post(PORT, "/api/chat", {"message": "/help"})
        assert status == 200 and "/add" in json.loads(body)["reply"], "chat help"
        status, body = post(PORT, "/api/chat", {"message": "hello?"})
        assert status == 200 and "unknown command" in json.loads(body)["reply"], "chat honest"
        status, body = post(PORT, "/api/vault-store", {"name": "T_KEY", "value": "s3cr3t", "kind": "service"})
        assert status == 200 and json.loads(body)["ok"], "vault deposit"
        status, body = get("/api/vault")
        listed = json.loads(body)["keys"]
        assert any(k["name"] == "T_KEY" for k in listed), "vault list"
        assert "s3cr3t" not in body.decode() and "cipher" not in body.decode(), "no secret material"
        print("PASS: health, state, tasks, decide, mcp, chat, vault")
        return 0
    finally:
        p.terminate()


def main_live():
    """Live-mode check against real reconcile. Shape only, statuses honest."""
    port = "8795"
    tmpdb = "/tmp/influence-live-test.db"
    try:
        os.remove(tmpdb)
    except OSError:
        pass
    env = dict(os.environ, DASH_PORT=port, LIVE="1", DASH_DB=tmpdb,
               PATH="/home/ubuntu/influence/.venv/bin:" + os.environ.get("PATH", ""))
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "server.py")], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd="/home/ubuntu/influence")
    try:
        for _ in range(150):
            try:
                status, body = get("/api/health", port)
                if status == 200:
                    break
            except Exception:
                time.sleep(0.4)
        else:
            print("FAIL: live server did not boot")
            return 1
        status, body = get("/api/state", port)
        assert status == 200, "live state status"
        d = json.loads(body)
        check_state_shape(d)
        assert d["influencers"] == [] and d["tasks"] == [], "backend clean by default"
        print("PASS live: clean empty state, honest shape")
        return 0
    finally:
        p.terminate()


def main_gated():
    """Token gate: everything except /api/health requires ?token= when DASH_TOKEN set."""
    import urllib.error
    port = "8796"
    env = dict(os.environ, DASH_PORT=port, DASH_TOKEN="test-token-123",
               DASH_JOURNAL="/tmp/dash-gate-test.db")
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "server.py")], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try:
                status, _ = get("/api/health", port)
                if status == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            print("FAIL: gated server did not boot")
            return 1
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=10)
            print("FAIL: ungated state with token set")
            return 1
        except urllib.error.HTTPError as e:
            assert e.code == 403, "gate"
        status, _ = get("/api/state?token=test-token-123", port)
        assert status == 200, "token passes"
        print("PASS gated: 403 without token, 200 with token")
        return 0
    finally:
        p.terminate()


if __name__ == "__main__":
    rc = main()
    if rc == 0 and os.environ.get("LIVE_TEST", "0") == "1":
        rc = main_live()
    if rc == 0:
        rc = main_gated()
    raise SystemExit(rc)
