"""Learn-loop tables + Jev rating runner + stats. Stdlib only.

Tables: content_items, content_features, performance_snapshots, strategy_weights.
Rating: Jev via OpenRouter (pinned typesafe/jev-1.13), 5 reps, pack_version pinned.
Stats: Spearman + permutation + BH + power gates (jev-writer methodology, ported).
"""
from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import subprocess
import urllib.request
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))
PACKS_DIR = os.path.join(_HERE, "packs")
JEV_MODEL = "typesafe/jev-1.13"

SCHEMA = """
CREATE TABLE IF NOT EXISTS content_items (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  channel TEXT NOT NULL,
  account TEXT NOT NULL,
  brand_slug TEXT DEFAULT 'oddhobb',
  kind TEXT DEFAULT 'post',
  title TEXT DEFAULT '',
  body TEXT DEFAULT '',
  hook_text TEXT DEFAULT '',
  external_id TEXT,
  url TEXT DEFAULT '',
  action_id INTEGER,
  receipt_id TEXT,
  release_id TEXT DEFAULT '',
  pack_hash TEXT DEFAULT '',
  creative_recipe TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS content_features (
  id INTEGER PRIMARY KEY,
  item_id INTEGER,
  pack_version TEXT NOT NULL,
  question_id TEXT NOT NULL,
  qtype TEXT NOT NULL,
  value REAL,
  choice_opt TEXT,
  agreement REAL,
  confidence REAL,
  reps INTEGER DEFAULT 5,
  rated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(item_id, pack_version, question_id),
  FOREIGN KEY (item_id) REFERENCES content_items(id)
);
CREATE TABLE IF NOT EXISTS performance_snapshots (
  id INTEGER PRIMARY KEY,
  item_id INTEGER,
  window TEXT NOT NULL,
  views INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  saves INTEGER DEFAULT 0,
  clicks INTEGER DEFAULT 0,
  orders INTEGER DEFAULT 0,
  followers_at_post INTEGER DEFAULT 0,
  reach_rate REAL,
  conversion_rate REAL,
  simulated INTEGER DEFAULT 0,
  taken_at TEXT DEFAULT (datetime('now')),
  UNIQUE(item_id, window),
  FOREIGN KEY (item_id) REFERENCES content_items(id)
);
CREATE TABLE IF NOT EXISTS strategy_weights (
  id INTEGER PRIMARY KEY,
  brand_slug TEXT DEFAULT 'oddhobb',
  channel TEXT DEFAULT 'all',
  pack_version TEXT NOT NULL,
  question_id TEXT NOT NULL,
  dim TEXT NOT NULL,
  outcome TEXT DEFAULT 'reach_rate',
  direction TEXT,
  rho REAL,
  p_value REAL,
  bh_pass INTEGER DEFAULT 0,
  n INTEGER,
  power TEXT,
  effect_size REAL,
  weight REAL DEFAULT 0,
  updated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(brand_slug, channel, pack_version, question_id, outcome)
);
"""


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_publication(channel: str, account: str, external_id: str,
                       receipt_id: str, hook_text: str = "", body: str = "",
                       title: str = "", url: str = "",
                       brand_slug: str = "oddhobb", kind: str = "post",
                       release_id: str | None = None, pack_hash: str = "",
                       creative_recipe: str = "", action_id: int | None = None,
                       db_path: str = DB_PATH) -> int:
    """Enter a publication into learning. (dir 33)

    Gate: external_id + receipt_id REQUIRED. Only PROVEN_TRUE published
    artifacts with independent verification enter content_items.
    Never learn from queued/failed/simulated output.
    Attaches release_id + pack_hash + creative recipe for attribution.
    """
    assert external_id, "external_id required (unverified output never enters)"
    assert receipt_id, "receipt_id required (no receipt, no learning)"
    db = _db(db_path)
    try:
        # migrate existing tables (release/pack/recipe columns)
        cols = [r[1] for r in db.execute("PRAGMA table_info(content_items)").fetchall()]
        for col in ("release_id", "pack_hash", "creative_recipe"):
            if col not in cols:
                db.execute(f"ALTER TABLE content_items ADD COLUMN {col} TEXT DEFAULT ''")
        cur = db.execute(
            "INSERT INTO content_items (at,channel,account,brand_slug,kind,title,"
            " body,hook_text,external_id,url,action_id,receipt_id,"
            " release_id,pack_hash,creative_recipe)"
            " VALUES (datetime('now'),?,?,?,?,?,?,?,?,?,?,?,?)",
            (channel, account, brand_slug, kind, title, body, hook_text,
             external_id, url, action_id, receipt_id,
             release_id or "", pack_hash, creative_recipe))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def _vault(key: str) -> str:
    try:
        return subprocess.run(
            ["agent-vault", "vault", "credential", "get", key, "--vault", "oracle"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


# ── packs ─────────────────────────────────────────────────────────────

def load_pack(pack_id: str) -> dict:
    path = os.path.join(PACKS_DIR, f"{pack_id}.json")
    with open(path) as f:
        return json.load(f)


def list_packs() -> list[str]:
    if not os.path.isdir(PACKS_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(PACKS_DIR) if f.endswith(".json"))


# ── Jev rating ────────────────────────────────────────────────────────

def _jev_call(state: dict, questions: dict, reps: int = 1) -> dict:
    key = _vault("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("no OPENROUTER_API_KEY")
    body = json.dumps({"model": JEV_MODEL, "state": state,
                       "questions": questions}).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/alpha/decisions", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "influence-learn/1.0")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _to_jev_questions(pack: dict) -> dict:
    """Pack questions → Jev API format (noul/choice/score)."""
    out = {}
    for q in pack["questions"]:
        qid = q["id"]
        if q["type"] == "bool":
            out[qid] = {"noul": {"question": q["question"]}}
        elif q["type"] == "score":
            out[qid] = {"score": {"question": q["question"],
                                  "criteria": q.get("criteria", []),
                                  "levels": q.get("levels", 5)}}
        elif q["type"] == "choice":
            out[qid] = {"choice": {"question": q["question"],
                                   "options": q.get("options", [])}}
    return out


def _build_state(pack: dict, item: dict) -> dict:
    state = {}
    for f in pack.get("stateFields", []):
        state[f] = item.get(f, "")
    return state


def _norm_answer(qtype: str, ans, levels: int = 5) -> tuple[float, str | None, float]:
    """Normalize one Jev answer to (value 0-1, choice_opt, confidence)."""
    if not isinstance(ans, dict):
        return 0.5, None, 0.0
    conf = float(ans.get("confidence", 0.5) or 0.5)
    if qtype == "bool":
        # noul → P(true)
        p = ans.get("noul", ans.get("probability", ans.get("p", 0.5)))
        if isinstance(p, dict):
            p = p.get("true", p.get("yes", 0.5))
        return max(0.0, min(1.0, float(p))), None, conf
    if qtype == "score":
        s = ans.get("score", ans.get("value", 0))
        if isinstance(s, dict):
            s = s.get("value", 0)
        try:
            v = (float(s) - 1) / max(1, (levels - 1))
        except (TypeError, ValueError):
            v = 0.5
        return max(0.0, min(1.0, v)), None, conf
    if qtype == "choice":
        opt = ans.get("choice", ans.get("option", ans.get("value")))
        p = ans.get("probability", ans.get("p", 0.5))
        if isinstance(opt, dict):
            # majority distribution
            opt, p = max(opt.items(), key=lambda kv: kv[1])
        return max(0.0, min(1.0, float(p))), str(opt), conf
    return 0.5, None, conf


def rate_item(item_id: int, pack_id: str, reps: int = 5,
               db_path: str = DB_PATH) -> dict:
    """Rate one content item with Jev. Stores features. Returns summary."""
    pack = load_pack(pack_id)
    pack_ver = f"{pack_id}@{pack.get('version', 'v1')}"
    db = _db(db_path)
    try:
        row = db.execute("SELECT hook_text,body,title FROM content_items WHERE id=?",
                         (item_id,)).fetchone()
        if not row:
            raise KeyError(f"no item {item_id}")
        item = {"hook_text": row[0] or "", "script_body": row[1] or "",
                "body": row[1] or "", "caption": row[2] or "", "title": row[2] or ""}
        state = _build_state(pack, item)
        jq = _to_jev_questions(pack)
        qmeta = {q["id"]: q for q in pack["questions"]}

        # collect reps
        by_q: dict[str, list] = {qid: [] for qid in jq}
        for _ in range(reps):
            ans = _jev_call(state, jq).get("answers", {})
            for qid in jq:
                if qid in ans:
                    by_q[qid].append(ans[qid])
        # aggregate + store
        rated = 0
        for qid, answers in by_q.items():
            if not answers:
                continue
            q = qmeta[qid]
            vals, opts, confs = [], [], []
            for a in answers:
                v, o, c = _norm_answer(q["type"], a, q.get("levels", 5))
                vals.append(v); confs.append(c)
                if o:
                    opts.append(o)
            mean_v = sum(vals) / len(vals)
            # agreement: 1 - normalized std
            sd = (sum((x - mean_v) ** 2 for x in vals) / len(vals)) ** 0.5 if len(vals) > 1 else 0
            agreement = max(0.0, 1.0 - sd * 2)
            mean_c = sum(confs) / len(confs) if confs else 0.5
            choice_opt = max(set(opts), key=opts.count) if opts else None
            db.execute(
                "INSERT OR REPLACE INTO content_features"
                " (item_id,pack_version,question_id,qtype,value,choice_opt,agreement,confidence,reps)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (item_id, pack_ver, qid, q["type"], mean_v, choice_opt,
                 agreement, mean_c, len(answers)))
            rated += 1
        db.commit()
        return {"ok": True, "item_id": item_id, "pack": pack_ver,
                "rated": rated, "reps": reps}
    finally:
        db.close()


# ── stats (jev-writer methodology, stdlib port) ───────────────────────

def _rank(xs: list[float]) -> list[float]:
    """Fractional ranks (average ties)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 3 or len(b) != n:
        return 0.0
    ra, rb = _rank(a), _rank(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db_ = sum((y - mb) ** 2 for y in rb) ** 0.5
    return num / (da * db_) if da and db_ else 0.0


def _residualize(y: list[float], x: list[float]) -> list[float]:
    """Rank-rank residuals of y on x (for partial correlation)."""
    ry, rx = _rank(y), _rank(x)
    n = len(y)
    mx, my = sum(rx) / n, sum(ry) / n
    b = sum((a - mx) * (c - my) for a, c in zip(rx, ry)) / (sum((a - mx) ** 2 for a in rx) or 1)
    return [c - (my + b * (a - mx)) for a, c in zip(rx, ry)]


def partial_spearman(vals: list[float], outcome: list[float],
                     control: list[float]) -> float:
    return spearman(_residualize(vals, control), _residualize(outcome, control))


def permutation_p(vals: list[float], outcome: list[float],
                  n_perm: int = 2000, seed: int = 42) -> float:
    """Two-sided permutation p-value for |rho|."""
    rng = random.Random(seed)
    obs = abs(spearman(vals, outcome))
    if obs == 0:
        return 1.0
    hits = 0
    idx = list(range(len(outcome)))
    for _ in range(n_perm):
        rng.shuffle(idx)
        if abs(spearman(vals, [outcome[i] for i in idx])) >= obs:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def benjamini_hochberg(pvals: list[float], alpha: float = 0.05) -> list[bool]:
    """BH FDR control. Returns pass/fail per test (input order)."""
    n = len(pvals)
    if not n:
        return []
    order = sorted(range(n), key=lambda i: pvals[i])
    passed = [False] * n
    thresh = 0
    for rank, i in enumerate(order, 1):
        if pvals[i] <= (rank / n) * alpha:
            thresh = rank
    for rank, i in enumerate(order, 1):
        if rank <= thresh:
            passed[i] = True
    return passed


def power_gate(n: int) -> tuple[str, dict]:
    """Sample-size gate. Returns (power, info)."""
    if n < 25:
        return "descriptive", {"note": "n<25: refuse correlations"}
    if n < 60:
        critical_r = math.tanh(1.96 / math.sqrt(max(1, n - 3)))
        mde = math.tanh(2.80 / math.sqrt(max(1, n - 3)))
        return "weak", {"criticalR": round(critical_r, 3), "MDE": round(mde, 3),
                        "E_FP": round(0.05, 3)}
    return "strong", {}


def analyze(brand_slug: str = "oddhobb", channel: str = "all",
            pack_id: str | None = None, db_path: str = DB_PATH) -> dict:
    """Run full analysis: features × outcomes → validated weights."""
    db = _db(db_path)
    try:
        # gather rated items with snapshots
        q = ("SELECT i.id, i.at, f.pack_version, f.question_id, f.value,"
             " s.reach_rate, s.conversion_rate FROM content_items i"
             " JOIN content_features f ON f.item_id=i.id"
             " JOIN performance_snapshots s ON s.item_id=i.id AND s.window='7d'"
             " AND (s.simulated IS NULL OR s.simulated=0)"
             " WHERE i.brand_slug=?")
        args: list = [brand_slug]
        if channel != "all":
            q += " AND i.channel=?"; args.append(channel)
        rows = db.execute(q, args).fetchall()
        if pack_id:
            rows = [r for r in rows if r[2].startswith(pack_id + "@")]

        # group by (pack_version, question_id)
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for item_id, at, pv, qid, val, rr, cr in rows:
            groups[(pv, qid)].append((val, rr or 0, cr or 0, at))

        # need pack directions
        results = []
        for (pv, qid), pts in groups.items():
            n = len(pts)
            power, pinfo = power_gate(n)
            if power == "descriptive":
                results.append({"pack": pv, "dim": qid, "n": n, "power": power,
                                "note": "refused: increase sample"})
                continue
            vals = [p[0] for p in pts]
            dates = []
            for p in pts:
                try:
                    dates.append(datetime.fromisoformat(p[3].replace("Z", "+00:00")).timestamp())
                except Exception:
                    dates.append(0)
            for outcome_name, oi in (("reach_rate", 1), ("conversion_rate", 2)):
                out = [p[oi] or 0 for p in pts]
                if len(set(out)) < 2 or len(set(vals)) < 2:
                    continue
                rho = partial_spearman(vals, out, dates)
                p = permutation_p(vals, out)
                results.append({"pack": pv, "dim": qid, "outcome": outcome_name,
                                "n": n, "power": power, "rho": round(rho, 3),
                                "p": round(p, 4), **{k: v for k, v in pinfo.items()}})
        # BH per outcome family
        for outcome_name in ("reach_rate", "conversion_rate"):
            fam = [r for r in results if r.get("outcome") == outcome_name and "p" in r]
            passes = benjamini_hochberg([r["p"] for r in fam])
            for r, ok in zip(fam, passes):
                r["bh_pass"] = bool(ok)
                # store weight
                pv, qid = r["pack"], r["dim"]
                pack = None
                try:
                    pack = load_pack(pv.split("@")[0])
                    direction = (pack.get("directions", {}) or {}).get(qid)
                except Exception:
                    direction = None
                db.execute(
                    "INSERT OR REPLACE INTO strategy_weights"
                    " (brand_slug,channel,pack_version,question_id,dim,outcome,direction,"
                    "  rho,p_value,bh_pass,n,power,effect_size,weight)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (brand_slug, channel, pv, qid, qid, r.get("outcome", "reach_rate"),
                     direction,
                     r["rho"], r["p"], 1 if ok else 0, r["n"], r["power"],
                     None, abs(r["rho"]) if ok else 0.0))
        db.commit()
        return {"ok": True, "dims": len(groups), "results": results}
    finally:
        db.close()


def weights(brand_slug: str = "oddhobb", channel: str = "all",
            validated_only: bool = True, db_path: str = DB_PATH) -> list[dict]:
    db = _db(db_path)
    try:
        q = ("SELECT pack_version,question_id,dim,direction,rho,p_value,n,power,weight"
             " FROM strategy_weights WHERE brand_slug=? AND channel=?")
        args = [brand_slug, channel]
        if validated_only:
            q += " AND bh_pass=1"
        q += " ORDER BY weight DESC"
        return [{"pack": r[0], "dim": r[2], "direction": r[3], "rho": r[4],
                 "p": r[5], "n": r[6], "power": r[7], "weight": r[8]}
                for r in db.execute(q, args).fetchall()]
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", action="store_true")
    ap.add_argument("--rate", nargs=2, metavar=("ITEM", "PACK"), default=None)
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--weights", action="store_true")
    ap.add_argument("--brand", default="oddhobb")
    ap.add_argument("--channel", default="all")
    args = ap.parse_args()
    if args.packs:
        print(list_packs())
    if args.rate:
        print(json.dumps(rate_item(int(args.rate[0]), args.rate[1]), indent=1))
    if args.analyze:
        r = analyze(args.brand, args.channel)
        print(f"dims={r.get('dims')} results={len(r.get('results', []))}")
        for x in r.get("results", [])[:20]:
            print(f"  {x.get('dim')}:{x.get('outcome')} n={x.get('n')} rho={x.get('rho')} p={x.get('p')} bh={x.get('bh_pass')} {x.get('power')}")
    if args.weights:
        for w in weights(args.brand, args.channel):
            print(f"  {w['dim']} {w['direction']} rho={w['rho']} n={w['n']} w={w['weight']}")
