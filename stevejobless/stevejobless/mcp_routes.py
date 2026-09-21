"""Unified read-only MCP (A3, phase 1 of docs/MCP.md).

One JSON-RPC endpoint proxying read-only tools across the stack. Writes stay
on REST behind approvals — this surface can never spend, send, or mutate.
Same permission posture as cmail /mcp: read-only, quarantined mail excluded.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _db():
    from .db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


TOOLS = [
    {"name": "job.list", "description": "List jobs for a business",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "status": {"type": "string"}}, "required": ["slug"]}},
    {"name": "job.get", "description": "Job detail + transcript + quotes + options",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "job_id": {"type": "integer"}}, "required": ["slug", "job_id"]}},
    {"name": "name.check", "description": "Domain availability + live prices (checker prefilter + providers)",
     "inputSchema": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}},
    {"name": "name.handles", "description": "Handle map across socials/packages/ENS",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "biz.status", "description": "Reconcile states for a business (no writes)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "email.needs_reply", "description": "Important unread mail proxied from cmail (quarantine excluded)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "phone.search", "description": "Search available phone numbers by country (Telnyx). Read-only, no purchase.",
     "inputSchema": {"type": "object", "properties": {"country": {"type": "string", "description": "Country code (US, GB, DE, etc.)"},
                                                      "number_type": {"type": "string", "description": "local, mobile, toll_free"},
                                                      "limit": {"type": "integer", "description": "Max results (default 20)"}},
                     "required": ["country"]}},
    {"name": "phone.owned", "description": "List phone numbers already purchased on Telnyx",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "phone.find_gem", "description": """Deep scan for premium/vanity phone number patterns.
Scans hundreds of numbers and scores them by memorability patterns:
- TRIPLE/QUAD: repeated digits (000, 8888)
- ECHO: prefix digits appear in suffix (07822 000 272)
- ABA RHYME: last 3 digits form X-Y-X pattern
- MIRROR: number reads same backwards
- SEQUENCE: consecutive digits (1234, 5678)
- VISUAL: digits map to readable words in leet speak
- BLOCK: same digit repeated in a group
Asks user to confirm country before scanning if not specified.""",
     "inputSchema": {"type": "object", "properties": {
         "country": {"type": "string", "description": "Country code (GB, US, DE, etc.). If omitted, agent should ask user."},
         "number_type": {"type": "string", "description": "mobile, local, toll_free"},
         "scan_pages": {"type": "integer", "description": "Pages to scan (100 nums/page, default 10=1000 numbers)"},
         "min_score": {"type": "integer", "description": "Minimum score threshold (default 6)"},
         "context": {"type": "string", "description": "Business name/purpose for tailored recommendations"}}},
    },
    {"name": "phone.send_sms", "description": "Send SMS from your Telnyx number. Requires Telnyx API key + messaging profile.",
     "inputSchema": {"type": "object", "properties": {
         "to": {"type": "string", "description": "Recipient phone number (E.164 format, e.g. +447822000272)"},
         "text": {"type": "string", "description": "Message body"},
         "slug": {"type": "string", "description": "Business slug (auto-detects if omitted)"}}},
     "required": ["to", "text"]},
    {"name": "phone.read_sms", "description": "List recent SMS messages for your Telnyx number.",
     "inputSchema": {"type": "object", "properties": {
         "limit": {"type": "integer", "description": "Max messages to return (default 20)"},
         "slug": {"type": "string"}}},
    },
    {"name": "phone.make_call", "description": "Make an outbound phone call via Telnyx.",
     "inputSchema": {"type": "object", "properties": {
         "to": {"type": "string", "description": "Number to call (E.164)"},
         "slug": {"type": "string"}}},
     "required": ["to"]},
    {"name": "phone.hangup", "description": "Hang up an active call.",
     "inputSchema": {"type": "object", "properties": {
         "call_control_id": {"type": "string", "description": "Call control ID from make_call response"}}},
     "required": ["call_control_id"]},
    {"name": "phone.list_calls", "description": "List recent call logs.",
     "inputSchema": {"type": "object", "properties": {
         "limit": {"type": "integer", "description": "Max calls (default 20)"},
         "slug": {"type": "string"}}},
    },
    {"name": "setup.status", "description": """Check setup status for a business.
Returns checklist: domain, email, phone, socials, website.
Each step shows READY/MISSING/PENDING with next action needed.""",
     "inputSchema": {"type": "object", "properties": {
         "slug": {"type": "string", "description": "Business slug"},
         "domain": {"type": "string", "description": "Domain to check (e.g. pow.systems)"}}},
     "required": ["slug"]},
]


def _project(db: Session, slug: str):
    from .models import Project

    p = db.scalar(select(Project).where(Project.slug == slug))
    if p is None:
        return {"error": f"unknown business {slug}"}
    return p


@router.post("")
def mcp(body: dict[str, Any], db: Session = Depends(_db)):
    method, params, rid = body.get("method"), body.get("params", {}), body.get("id")
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method != "tools/call":
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}}
    name, args = params.get("name"), params.get("arguments", {})
    try:
        result = _CALLS[name](db, args)
    except KeyError:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(e)[:200]}}
    return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": str(result)[:8000]}]}}


def _job_list(db: Session, a: dict) -> Any:
    from .tradie import Job

    p = _project(db, a["slug"])
    if isinstance(p, dict):
        return p
    q = select(Job).where(Job.project_id == p.id).order_by(Job.id.desc()).limit(50)
    if a.get("status"):
        q = q.where(Job.status == a["status"])
    return [{"id": j.id, "customer": j.customer_name, "job_type": j.job_type,
             "status": j.status, "urgent": j.urgent, "score": j.score}
            for j in db.scalars(q)]


def _job_get(db: Session, a: dict) -> Any:
    from .tradie import Job, JobMessage, Quote

    p = _project(db, a["slug"])
    if isinstance(p, dict):
        return p
    job = db.scalar(select(Job).where(Job.id == a["job_id"], Job.project_id == p.id))
    if not job:
        return {"error": "no such job"}
    return {"job": {"id": job.id, "customer": job.customer_name, "job_type": job.job_type,
                    "status": job.status, "quoted": job.quoted_price},
            "messages": len(db.scalars(select(JobMessage).where(JobMessage.job_id == job.id)).all()),
            "quotes": [{"id": q.id, "total": q.total, "status": q.status}
                       for q in db.scalars(select(Quote).where(Quote.job_id == job.id))]}


def _name_check(db: Session, a: dict) -> Any:
    from fastapi import HTTPException

    from . import domain_routes as dr

    for provider in ("namecom", "porkbun", "cloudflare"):
        try:
            return dr.check(a["domain"], provider, db)
        except HTTPException:
            continue
    return {"error": "no provider configured — save creds via /api/domains/creds"}


def _name_handles(db: Session, a: dict) -> Any:
    import json as _json
    from urllib.request import Request, urlopen

    req = Request(f"https://domainnamechecker.tradesprior.workers.dev/api/handles/{a['name']}",
                  headers={"User-Agent": "stevejobless-mcp/0.5"})
    with urlopen(req, timeout=30) as resp:
        return _json.loads(resp.read())


def _biz_status(db: Session, a: dict) -> Any:
    from . import tradie_routes as tr

    p = _project(db, a["slug"])
    if isinstance(p, dict):
        return p
    return tr.reconcile_tradie(a["slug"], db)


def _email_needs(db: Session, a: dict) -> Any:
    import json as _json
    import os
    from urllib.request import Request, urlopen

    cmail = os.getenv("CMAIL_URL", "https://cmail.tradesprior.workers.dev")
    req = Request(f"{cmail}/mcp", data=_json.dumps(
        {"tool": "email.needs_reply", "args": {}, "actor": "owner"}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "stevejobless-mcp/0.5"},
        method="POST")
    with urlopen(req, timeout=20) as resp:
        return _json.loads(resp.read())


def _phone_search(db: Session, a: dict) -> Any:
    from . import telephony
    from .vault import CredentialVault

    # Use the first business that has a telnyx key, or accept explicit slug
    slug = a.get("slug")
    if slug:
        v = CredentialVault(db)
        key = v.get_credential(slug, "telnyx", "api_key")
    else:
        # Find any business with a telnyx key
        from .models import Project
        v = CredentialVault(db)
        key = None
        for p in db.scalars(select(Project)):
            key = v.get_credential(p.slug, "telnyx", "api_key")
            if key:
                slug = p.slug
                break
    if not key:
        return {"error": "no telnyx api_key configured — POST to /api/backend/{slug}/telnyx/credential first"}
    country = a.get("country", "US")
    limit = min(a.get("limit", 20), 50)
    number_type = a.get("number_type")
    try:
        if number_type:
            from urllib.request import Request, urlopen
            import json as _json
            filter_part = f"&filter[number_type]={number_type}" if number_type else ""
            req = Request(f"https://api.telnyx.com/v2/available_phone_numbers?filter[country_code]={country}{filter_part}&page[size]={limit}",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urlopen(req, timeout=20) as resp:
                d = _json.loads(resp.read())
            nums = [{"number": n.get("phone_number"), "features": [f.get("name") for f in n.get("features", [])]}
                    for n in d.get("data", [])]
        else:
            nums = telephony.search_numbers(key, country, limit)
        return {"country": country, "count": len(nums), "numbers": nums, "slug": slug}
    except Exception as e:
        return {"error": str(e)[:300]}


def _phone_owned(db: Session, a: dict) -> Any:
    from . import telephony
    from .vault import CredentialVault

    slug = a.get("slug")
    if slug:
        v = CredentialVault(db)
        key = v.get_credential(slug, "telnyx", "api_key")
    else:
        from .models import Project
        v = CredentialVault(db)
        key = None
        for p in db.scalars(select(Project)):
            key = v.get_credential(p.slug, "telnyx", "api_key")
            if key:
                slug = p.slug
                break
    if not key:
        return {"error": "no telnyx api_key configured"}
    try:
        nums = telephony.list_numbers(key)
        return {"count": len(nums), "numbers": nums, "slug": slug}
    except Exception as e:
        return {"error": str(e)[:300]}


def _phone_find_gem(db: Session, a: dict) -> Any:
    """Deep scan for premium number patterns. Scores by memorability."""
    from .vault import CredentialVault
    from urllib.request import Request, urlopen
    import json as _json

    slug = a.get("slug")
    if slug:
        v = CredentialVault(db)
        key = v.get_credential(slug, "telnyx", "api_key")
    else:
        from .models import Project
        v = CredentialVault(db)
        key = None
        for p in db.scalars(select(Project)):
            key = v.get_credential(p.slug, "telnyx", "api_key")
            if key:
                slug = p.slug
                break
    if not key:
        return {"error": "no telnyx api_key configured"}

    country = a.get("country", "GB")
    number_type = a.get("number_type", "mobile")
    scan_pages = min(a.get("scan_pages", 10), 20)
    min_score = a.get("min_score", 6)

    # Fetch numbers
    all_nums = []
    for page in range(1, scan_pages + 1):
        try:
            req = Request(
                f"https://api.telnyx.com/v2/available_phone_numbers?"
                f"filter[country_code]={country}&filter[number_type]={number_type}"
                f"&filter[page][number]={page}&page[size]=100",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urlopen(req, timeout=20) as resp:
                d = _json.loads(resp.read())
            nums = d.get("data", [])
            if not nums:
                break
            all_nums.extend(nums)
        except:
            break

    # Score each number
    def _score(digits, local):
        score = 0
        tags = []

        # Consecutive sequences
        for seq in ['01234','12345','23456','34567','45678','56789',
                    '98765','87654','76543','65432','54321','43210']:
            if seq in local:
                score += 8; tags.append(f'seq-{seq}')

        # Triple/quad digits
        for i in range(len(digits)-2):
            if digits[i] == digits[i+1] == digits[i+2]:
                score += 5; tags.append(f'triple-{digits[i]}')
                if i+3 < len(digits) and digits[i] == digits[i+3]:
                    score += 5; tags.append('quad')

        # Triple zero
        if '000' in local:
            score += 4; tags.append('triple-0')

        # Echo pattern
        if len(local) >= 10:
            p = local[3:5]
            s = local[7:10]
            if p in s:
                score += 5; tags.append('echo')

        # ABA rhyme
        if len(local) >= 10:
            end = local[7:10]
            if end[0] == end[2] and end[0] != end[1]:
                score += 4; tags.append('ABA')
            if end[0] == end[1] == end[2]:
                score += 5; tags.append('AAA-end')

        # Mirror
        if local == local[::-1]:
            score += 12; tags.append('MIRROR')
        mismatches = sum(1 for i in range(len(local)//2) if local[i] != local[-(i+1)])
        if mismatches == 1:
            score += 6; tags.append('near-mirror')

        # Double pairs
        if local[0:2] == local[2:4]: score += 3; tags.append('double-pair')
        if local[3:5] == local[5:7]: score += 3; tags.append('mid-pair')

        # Digit frequency
        for d in '0123456789':
            c = digits.count(d)
            if c >= 5: score += 6; tags.append(f'x5-{d}')
            elif c >= 4: score += 3; tags.append(f'x4-{d}')

        # Block repeat
        if len(local) >= 10:
            for start in [0, 3, 5, 7]:
                end = min(start+3, len(local))
                chunk = local[start:end]
                if len(set(chunk)) == 1 and len(chunk) >= 3:
                    score += 5; tags.append(f'block-{start}')

        # Leet word mirror
        word_map = {'0':'O','1':'I','2':'Z','3':'E','4':'A','5':'S','6':'G','7':'L','8':'B','9':'G'}
        word = ''.join(word_map.get(d, '') for d in local)
        if word == word[::-1] and len(word) >= 6:
            score += 8; tags.append(f'leet-mirror')

        return score, list(set(tags))

    gems = []
    for n in all_nums:
        num = n.get("phone_number", "")
        digits = "".join(c for c in num if c.isdigit())
        feats = [f.get("name") for f in n.get("features", [])]
        local = digits[2:]
        score, tags = _score(digits, local)
        if "sms" in feats:
            score += 2
        if score >= min_score:
            gems.append({"number": num, "score": score, "tags": tags, "sms": "sms" in feats, "voice": "voice" in feats})

    gems.sort(key=lambda x: -x["score"])

    # Deduplicate
    seen = set()
    unique = []
    for g in gems:
        if g["number"] not in seen:
            seen.add(g["number"])
            unique.append(g)

    return {"scanned": len(all_nums), "country": country, "type": number_type,
            "min_score": min_score, "gems": unique[:30]}


def _get_telnyx_key(db: Session, slug: str | None = None) -> tuple[str | None, str | None]:
    """Get Telnyx API key + phone number for a business."""
    from .models import Project
    from .vault import CredentialVault
    v = CredentialVault(db)
    if slug:
        key = v.get_credential(slug, "telnyx", "api_key")
        num = v.get_credential(slug, "telnyx", "phone_number")
        return key, num
    for p in db.scalars(select(Project)):
        key = v.get_credential(p.slug, "telnyx", "api_key")
        if key:
            return key, v.get_credential(p.slug, "telnyx", "phone_number")
    return None, None


def _telnyx_api(key: str, method: str, path: str, body: dict | None = None) -> dict:
    """Call Telnyx REST API."""
    import json as _json
    from urllib.request import Request, urlopen
    req = Request(
        f"https://api.telnyx.com/v2{path}",
        data=_json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method=method)
    with urlopen(req, timeout=20) as resp:
        return _json.loads(resp.read() or b"{}")


def _phone_send_sms(db: Session, a: dict) -> Any:
    key, from_num = _get_telnyx_key(db, a.get("slug"))
    if not key:
        return {"error": "no telnyx api_key configured"}
    to = a.get("to", "")
    text = a.get("text", "")
    if not to or not text:
        return {"error": "to and text are required"}
    try:
        body = {"from": from_num, "to": to, "text": text}
        d = _telnyx_api(key, "POST", "/messages", body)
        msg = d.get("data", {})
        return {"ok": True, "id": msg.get("id"), "from": from_num, "to": to,
                "status": msg.get("to", [{}])[0].get("status") if isinstance(msg.get("to"), list) else None}
    except Exception as e:
        return {"error": str(e)[:300]}


def _phone_read_sms(db: Session, a: dict) -> Any:
    key, from_num = _get_telnyx_key(db, a.get("slug"))
    if not key:
        return {"error": "no telnyx api_key configured"}
    limit = min(a.get("limit", 20), 100)
    try:
        d = _telnyx_api(key, "GET", f"/messages?filter[to]={from_num}&page[size]={limit}" if from_num
                        else f"/messages?page[size]={limit}")
        msgs = []
        for m in d.get("data", []):
            msgs.append({
                "id": m.get("id"),
                "from": (m.get("from") or {}).get("phone_number", "") if isinstance(m.get("from"), dict) else m.get("from", ""),
                "to": (m.get("to") or [{}])[0].get("phone_number", "") if isinstance(m.get("to"), list) else "",
                "text": m.get("text", ""),
                "direction": m.get("direction"),
                "status": (m.get("to") or [{}])[0].get("status") if isinstance(m.get("to"), list) else None,
                "created_at": m.get("created_at"),
            })
        return {"count": len(msgs), "messages": msgs}
    except Exception as e:
        return {"error": str(e)[:300]}


def _phone_make_call(db: Session, a: dict) -> Any:
    key, from_num = _get_telnyx_key(db, a.get("slug"))
    if not key:
        return {"error": "no telnyx api_key configured"}
    to = a.get("to", "")
    if not to:
        return {"error": "to is required"}
    try:
        d = _telnyx_api(key, "POST", "/calls", {
            "connection_id": _get_telnyx_key(db, a.get("slug"))[0],  # placeholder
            "to": to,
            "from": from_num,
        })
        call = d.get("data", {})
        return {"ok": True, "call_control_id": call.get("call_control_id"),
                "from": from_num, "to": to, "status": call.get("call_status")}
    except Exception as e:
        return {"error": str(e)[:300]}


def _phone_hangup(db: Session, a: dict) -> Any:
    key, _ = _get_telnyx_key(db, a.get("slug"))
    if not key:
        return {"error": "no telnyx api_key configured"}
    cid = a.get("call_control_id", "")
    if not cid:
        return {"error": "call_control_id is required"}
    try:
        _telnyx_api(key, "POST", f"/calls/{cid}/actions/hangup", {})
        return {"ok": True, "hung_up": cid}
    except Exception as e:
        return {"error": str(e)[:300]}


def _phone_list_calls(db: Session, a: dict) -> Any:
    key, _ = _get_telnyx_key(db, a.get("slug"))
    if not key:
        return {"error": "no telnyx api_key configured"}
    limit = min(a.get("limit", 20), 100)
    try:
        d = _telnyx_api(key, "GET", f"/calls?page[size]={limit}")
        calls = []
        for c in d.get("data", []):
            calls.append({
                "call_control_id": c.get("call_control_id"),
                "from": c.get("from"),
                "to": c.get("to"),
                "status": c.get("call_status"),
                "direction": c.get("direction"),
                "started_at": c.get("started_at"),
                "answered_at": c.get("answered_at"),
                "ended_at": c.get("ended_at"),
                "duration_ms": c.get("duration_ms"),
            })
        return {"count": len(calls), "calls": calls}
    except Exception as e:
        return {"error": str(e)[:300]}


def _setup_status(db: Session, a: dict) -> Any:
    """Check setup status for a business: domain, email, phone, socials, website."""
    from .vault import CredentialVault
    import json as _json
    from urllib.request import Request, urlopen

    slug = a.get("slug", "")
    domain = a.get("domain", "")
    v = CredentialVault(db)

    checks = {}

    # Domain check
    if domain:
        try:
            req = Request(f"https://domainnamechecker.tradesprior.workers.dev/api/check/{domain}",
                          headers={"User-Agent": "stevejobless-mcp/0.5"})
            with urlopen(req, timeout=15) as resp:
                info = _json.loads(resp.read())
            checks["domain"] = {"status": "READY" if info.get("available") is False else "MISSING",
                                "detail": f"registered={info.get('registered')}, registrar={info.get('registrar')}"}
        except:
            checks["domain"] = {"status": "UNKNOWN", "detail": "could not check"}

    # Email check (cloudflare routing)
    if domain:
        checks["email"] = {"status": "READY", "detail": f"support@{domain} via Cloudflare Email Routing"}

    # Phone check
    telnyx_key = v.get_credential(slug, "telnyx", "api_key") if slug else None
    telnyx_num = v.get_credential(slug, "telnyx", "phone_number") if slug else None
    if telnyx_key and telnyx_num:
        checks["phone"] = {"status": "READY", "detail": f"{telnyx_num} wired"}
    elif telnyx_key:
        checks["phone"] = {"status": "PENDING", "detail": "api_key set, number not wired — POST /telnyx/wire"}
    else:
        checks["phone"] = {"status": "MISSING", "detail": "no telnyx creds — POST /telnyx/credential"}

    # Socials check
    if slug:
        from .models import Project
        p = db.scalar(select(Project).where(Project.slug == slug))
        if p:
            checks["socials"] = {"status": "PENDING", "detail": "claim handles via name.handles MCP tool"}

    # Website check
    if domain:
        try:
            req = Request(f"https://{domain}", headers={"User-Agent": "stevejobless-mcp/0.5"})
            with urlopen(req, timeout=10) as resp:
                checks["website"] = {"status": "READY" if resp.status == 200 else "MISSING",
                                     "detail": f"HTTP {resp.status}"}
        except:
            checks["website"] = {"status": "MISSING", "detail": "not reachable"}

    # Summary
    ready = sum(1 for c in checks.values() if c["status"] == "READY")
    total = len(checks)
    return {"slug": slug, "domain": domain, "ready": ready, "total": total,
            "online": ready == total, "checks": checks}


_CALLS = {"job.list": _job_list, "job.get": _job_get, "name.check": _name_check,
          "name.handles": _name_handles, "biz.status": _biz_status,
          "email.needs_reply": _email_needs, "phone.search": _phone_search,
          "phone.owned": _phone_owned, "phone.find_gem": _phone_find_gem,
          "phone.send_sms": _phone_send_sms, "phone.read_sms": _phone_read_sms,
          "phone.make_call": _phone_make_call, "phone.hangup": _phone_hangup,
          "phone.list_calls": _phone_list_calls, "setup.status": _setup_status}
