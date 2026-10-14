"""Audio flow — Fish Audio studio via MCP, grant-gated like images_flow.

SPEND POLICY (owner law, 2026-10-14): ZERO package credits, ever, until
the owner explicitly says otherwise. Enforced structurally, not by
convention: every live (spending) path checks _spend_allowed(), which
requires CREDIT_SPEND_ENABLED=1 in the server environment. Default off —
grants, approvals, and fulfills all fail closed without it. Free reads
and the $0 REST tier always work.
"""
from __future__ import annotations

import hashlib
import json
import os

# 1 package credit per UTF-8 byte of spoken text (2x for another team's pro clone).
CREDITS_PER_BYTE = 1


def _fish():
    try:
        from providers import fish_mcp
    except ImportError:
        from pipeline.providers import fish_mcp
    return fish_mcp


def tts_quote(text: str, pro_clone_2x: bool = False) -> dict:
    """Pure credit math for a TTS request. No network, no spend."""
    n = len(text.encode("utf-8"))
    mult = 2 if pro_clone_2x else 1
    return {"bytes": n, "credits": n * mult * CREDITS_PER_BYTE,
            "multiplier": mult}


def balance() -> dict:
    """Free read: plan, remaining credits, per-call TTS budget."""
    return _fish().balance()


def voices(query: str = "", language: str = "", self_only: bool = False,
           page_size: int = 10) -> dict:
    """Free read: voice casting search."""
    return _fish().search_voices(query, language, self_only, page_size)


def voice_detail(voice_id: str) -> dict:
    """Free read: one voice — description, tags, sample, popularity."""
    if not voice_id:
        return {"ok": False, "reason": "voice_id required"}
    return _fish().call_tool("get_voice", {"voice_id": voice_id})


def workspaces() -> dict:
    """Free read: team workspaces (needed for media generation)."""
    return _fish().list_workspaces()


def media_models(media_type: str = "", capability: str = "") -> dict:
    """Free read: image/video model list with default credit prices."""
    return _fish().list_media_models(media_type, capability)


def estimate_media(kind: str, workspace_id: str, model_id: str, prompt: str,
                  operation: str = "t2v") -> dict:
    """Free server-side quote. kind=image|video. Read-only, no task created."""
    if kind == "image":
        return _fish().estimate_image(workspace_id, model_id, prompt)
    if kind == "video":
        return _fish().estimate_video(workspace_id, model_id, prompt, operation)
    return {"ok": False, "reason": f"kind={kind}: use image|video"}


def _payload_hash(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def speak(text: str, voice_id: str, dry_run: bool = True,
          ctx: dict | None = None, brand: str = "oddhobb",
          campaign: str | None = None) -> dict:
    """TTS with grant gate.

    dry_run (default): pure preview — credit quote + payload hash for the
    human to approve. live=True: requires ctx grant; executes via
    runtime.execute (generate_paid) → permanent audio URL + receipt.
    """
    if not text or not voice_id:
        return {"ok": False, "reason": "text and voice_id required"}
    q = tts_quote(text)
    payload = {"tool": "text_to_speech", "text": text, "voice_id": voice_id,
               "credits": q["credits"]}
    sha = _payload_hash(payload)
    if dry_run:
        return {"ok": True, "dry_run": True, "quote": q,
                "payload": {**payload, "text_chars": len(text)},
                "payload_hash": sha,
                "next": "human approves payload hash → live call with grant"}
    if not ctx or not ctx.get("grant"):
        return {"ok": False,
                "reason": "no execution context with verified grant: FAIL CLOSED. "
                          "Run dry-run first, approve payload hash, then call "
                          "with ctx.grant."}
    blocked = _spend_allowed()
    if blocked:
        return blocked
    try:
        from runtime import make_spec, execute
    except ImportError:
        from pipeline.runtime import make_spec, execute

    spec = make_spec(brand, "audio.speak", "generate_paid",
                     "pipeline.providers.fish_mcp:call_tool",
                     f"tts:{voice_id}:{sha[:12]}", payload,
                     campaign=campaign, expected_cost_usd=0.0)

    def _exec():
        r = _fish().call_tool("text_to_speech",
                              {"text": text, "voice_id": voice_id})
        if not r.get("ok"):
            return {"ok": False, "response": {"reason": r.get("reason")}}
        return {"ok": True, "external_id": f"fish-tts:{sha[:12]}",
                "response": {"result": r.get("data"),
                             "credits_quoted": q["credits"]}}

    res = execute(spec, ctx["grant"], _exec)
    return {"ok": res.get("ok", False), **res}


def generate_media(kind: str, workspace_id: str, model_id: str, prompt: str,
                   expected_credits: int, pricing_version: str = "",
                   idempotency_key: str = "", dry_run: bool = True,
                   ctx: dict | None = None, brand: str = "oddhobb",
                   operation: str = "t2v",
                   campaign: str | None = None) -> dict:
    """Media generation with grant gate. dry_run returns the free estimate
    + the exact live payload hash (one construction — dry and live can
    never drift); live requires ctx grant AND human-confirmed credits."""
    tool = "generate_image" if kind == "image" else "generate_video"
    args: dict = {"workspace_id": workspace_id, "model_id": model_id,
                  "prompt": prompt, "expected_credits": expected_credits}
    if pricing_version:
        args["pricing_version"] = pricing_version
    if idempotency_key:
        args["idempotency_key"] = idempotency_key
    if kind == "video":
        args["operation"] = operation
    payload = {"tool": tool, **args}
    if dry_run:
        return {"ok": True, "dry_run": True,
                "estimate": estimate_media(kind, workspace_id, model_id,
                                           prompt, operation),
                "payload": payload,
                "payload_hash": _payload_hash(payload),
                "next": "human approves estimate → live call with grant + "
                        "expected_credits"}
    if not ctx or not ctx.get("grant"):
        return {"ok": False,
                "reason": "no execution context with verified grant: FAIL CLOSED."}
    blocked = _spend_allowed()
    if blocked:
        return blocked
    try:
        from runtime import make_spec, execute
    except ImportError:
        from pipeline.runtime import make_spec, execute
    spec = make_spec(brand, f"audio.{tool}", "generate_paid",
                     "pipeline.providers.fish_mcp:call_tool",
                     f"{kind}:{model_id}:{_payload_hash(payload)[:12]}", payload,
                     campaign=campaign, expected_cost_usd=0.0)

    def _exec():
        r = _fish().call_tool(tool, args)
        if not r.get("ok"):
            return {"ok": False, "response": {"reason": r.get("reason")}}
        return {"ok": True, "external_id": f"fish-{kind}:{model_id}",
                "response": {"result": r.get("data"),
                             "credits_expected": expected_credits}}

    res = execute(spec, ctx["grant"], _exec)
    return {"ok": res.get("ok", False), **res}


# ---- Story Studio (native longform: project → blocks → generate → export)
#
# Division with tts_text: OUR prep (clean/normalize/score/tag-protect) runs
# FIRST (garbage-in protection + worthiness gate). Studio's import LLM then
# does structure (chapters/blocks), voice casting, delivery tags — free.
# Our chunk-loop stays as the short-snippet path; Studio owns episodes.

def studio_create(name: str, roster: dict, chapters: list,
                  default_voice_id: str = "") -> dict:
    """Free: structured project (≤200 blocks — bigger goes via import)."""
    if not name:
        return {"ok": False, "reason": "name required"}
    args: dict = {"name": name, "roster": roster, "chapters": chapters}
    if default_voice_id:
        args["default_voice_id"] = default_voice_id
    return _fish().call_tool("studio_create_project", args)


def studio_import(text: str = "", name: str = "", rewrite: bool = True,
                  auto_tags: bool = True) -> dict:
    """Free: raw script/doc (≤1.5M chars) → background LLM structures it.
    Returns immediately; poll studio_status(). Platform pays the LLM."""
    if not text:
        return {"ok": False, "reason": "text required"}
    return _fish().call_tool("studio_import_document",
                             {"text": text, "name": name or "episode",
                              "rewrite": rewrite, "auto_tags": auto_tags})


def studio_status(project_id: str) -> dict:
    """Free poll: chapters, dirty counts, roster, job state."""
    if not project_id:
        return {"ok": False, "reason": "project_id required"}
    return _fish().call_tool("studio_project", {"project_id": project_id})


def studio_read(project_id: str, chapter: str = "",
                fmt: str = "") -> dict:
    """Free: read blocks (anchor, rev, voice, text, dirty, duration)."""
    args: dict = {"project_id": project_id}
    if chapter:
        args["chapter"] = chapter
    if fmt:
        args["format"] = fmt
    return _fish().call_tool("studio_read_blocks", args)


def studio_enhance(text: str) -> dict:
    """Free platform-tuned polish: expands numbers/dates/symbols, adds
    delivery tags at studio density. Run BEFORE import for best results."""
    if not text:
        return {"ok": False, "reason": "text required"}
    return _fish().call_tool("studio_enhance_text", {"text": text})


def studio_recast(project_id: str, from_voice_id: str,
                  to_voice_id: str) -> dict:
    """Free: swap one voice across the whole project (blocks go dirty)."""
    return _fish().call_tool("studio_recast_speaker",
                             {"project_id": project_id,
                              "from_voice_id": from_voice_id,
                              "to_voice_id": to_voice_id})


def _spend_allowed() -> dict | None:
    """Owner kill-switch: credit spend needs explicit env opt-in."""
    import os as _os2
    if _os2.environ.get("CREDIT_SPEND_ENABLED", "") != "1":
        return {"ok": False,
                "reason": "CREDIT SPEND DISABLED by owner policy (0 credits "
                          "until owner says otherwise). Free tier only."}
    return None


def _need_grant(ctx: dict | None) -> dict | None:
    if not ctx or not ctx.get("grant"):
        return {"ok": False,
                "reason": "no execution context with verified grant: FAIL "
                          "CLOSED. Dry-run first, approve the quote, then "
                          "call with ctx.grant."}
    return _spend_allowed()  # owner kill-switch even with a valid grant


def studio_generate(project_id: str, chapter: str = "",
                    blocks: list | None = None, dry_run: bool = True,
                    ctx: dict | None = None,
                    brand: str = "sleepdraw",
                    campaign: str | None = None) -> dict:
    """Render blocks. dry_run (default) → FREE server quote. live → grant +
    runtime.execute (generate_paid). Unchanged/cached blocks always free."""
    if not project_id:
        return {"ok": False, "reason": "project_id required"}
    if dry_run:
        return _fish().call_tool("studio_generate",
                                 {"project_id": project_id,
                                  **({"chapter": chapter} if chapter else {}),
                                  **({"blocks": blocks} if blocks else {}),
                                  "dry_run": True})
    err = _need_grant(ctx)
    if err:
        return err
    try:
        from runtime import make_spec, execute
    except ImportError:
        from pipeline.runtime import make_spec, execute
    payload = {"tool": "studio_generate", "project_id": project_id,
               "chapter": chapter, "blocks": blocks or []}
    spec = make_spec(brand, "audio.studio.generate", "generate_paid",
                     "pipeline.providers.fish_mcp:call_tool",
                     f"studio:{project_id}:{_payload_hash(payload)[:12]}",
                     payload, campaign=campaign, expected_cost_usd=0.0)

    def _exec():
        r = _fish().call_tool("studio_generate",
                              {"project_id": project_id,
                               **({"chapter": chapter} if chapter else {}),
                               **({"blocks": blocks} if blocks else {})})
        if not r.get("ok"):
            return {"ok": False, "response": {"reason": r.get("reason")}}
        return {"ok": True, "external_id": f"fish-studio:{project_id}",
                "response": {"result": r.get("data")}}

    res = execute(spec, ctx["grant"], _exec)
    return {"ok": res.get("ok", False), **res}


def studio_export(project_id: str, fmt: str = "mp3",
                  confirmed_credits: int | None = None,
                  chapters: list | None = None,
                  ctx: dict | None = None, brand: str = "sleepdraw",
                  campaign: str | None = None) -> dict:
    """Export master audio. No confirmed_credits → FREE quote
    {blocks_to_generate, credits} (no grant needed — read-only).
    With confirmed credits → grant + runtime.execute → background job."""
    if not project_id:
        return {"ok": False, "reason": "project_id required"}
    if confirmed_credits is None:
        args: dict = {"project_id": project_id, "format": fmt}
        if chapters:
            args["chapters"] = chapters
        return _fish().call_tool("studio_export", args)
    err = _need_grant(ctx)
    if err:
        return err
    try:
        from runtime import make_spec, execute
    except ImportError:
        from pipeline.runtime import make_spec, execute
    payload = {"tool": "studio_export", "project_id": project_id,
               "format": fmt, "chapters": chapters or [],
               "confirmed_credits": confirmed_credits}
    spec = make_spec(brand, "audio.studio.export", "generate_paid",
                     "pipeline.providers.fish_mcp:call_tool",
                     f"studio-exp:{project_id}:{_payload_hash(payload)[:12]}",
                     payload, campaign=campaign, expected_cost_usd=0.0)

    def _exec():
        args: dict = {"project_id": project_id, "format": fmt}
        if chapters:
            args["chapters"] = chapters
        if confirmed_credits is not None:
            args["confirmed_credits"] = confirmed_credits
        r = _fish().call_tool("studio_export", args)
        if not r.get("ok"):
            return {"ok": False, "response": {"reason": r.get("reason")}}
        return {"ok": True, "external_id": f"fish-exp:{project_id}",
                "response": {"result": r.get("data")}}

    res = execute(spec, ctx["grant"], _exec)
    return {"ok": res.get("ok", False), **res}


# ---- pull: Fish project → OUR storyboard file (vendor independence) ----
#
# Fish's free intelligence (import LLM structuring, casting, auto-tags)
# produces the structure; we store it in OUR format in OUR repo and can
# render it on ANY backend (fish/edge/eleven/qwen). Fish projects become
# scratch; our files are truth. Re-pull anytime to refresh.

def studio_pull(project_id: str) -> dict:
    """Free: read full project → our storyboard schema.

    Our block: {anchor, chapter, voice_id, voice (name), kind,
    text (tags intact), rev}. Compatible with easy's storyboard elements
    (type/speaker/text/instruct) plus fish provenance.
    """
    if not project_id:
        return {"ok": False, "reason": "project_id required"}
    st = studio_status(project_id)
    if not st.get("ok"):
        return st
    data = st.get("data") or {}
    roster = {}
    for sp in (data.get("speakers") or data.get("roster") or []):
        if isinstance(sp, dict):
            roster[sp.get("name") or sp.get("id", "")] = sp
    chapters = data.get("chapters") or []
    blocks_out = []
    for ch in chapters:
        anchor = ch.get("anchor") if isinstance(ch, dict) else ch
        if not anchor:
            continue
        r = studio_read(project_id, chapter=anchor)
        for b in ((r.get("data") or {}).get("blocks") or []):
            vname = b.get("voice", "")
            blocks_out.append({
                "anchor": b.get("anchor", ""),
                "chapter": anchor,
                "chapter_title": ch.get("title", "") if isinstance(ch, dict) else "",
                "voice_id": (roster.get(vname) or {}).get("voice_id", vname)
                if vname in roster else vname,
                "voice": vname,
                "kind": b.get("kind", "speech"),
                "text": b.get("text", ""),
                "rev": b.get("rev", ""),
                "duration": b.get("duration", 0),
            })
    return {"ok": True, "project_id": project_id,
            "title": data.get("name", project_id),
            "roster": roster, "chapters": chapters,
            "blocks": blocks_out, "n_blocks": len(blocks_out),
            "credits_total": sum(len((b.get("text") or "").encode())
                                 for b in blocks_out)}


# ---- $0 pro render (REST s2.1-pro-free — no credits, no dollars) ----
#
# Studio audio always bills package credits. THIS path bills nothing:
# same pro quality, fair-use free tier. Default for snippets, casting,
# and bulk narration. Drama/multi-speaker stays on the grant-gated MCP.

def speak_free(text: str, voice_id: str, out_path: str = "",
               speed: float = 1.0, volume_db: float = 0.0,
               temperature: float | None = None) -> dict:
    """$0 TTS via REST free tier. No grant needed (no consequence), but
    callers log it. Paid models are unreachable from here by construction.
    Fish knobs: speed 0.5-2.0 (sleep ~0.72-0.85), volume dB, temp 0-1."""
    try:
        from providers import fish_rest
    except ImportError:
        from pipeline.providers import fish_rest
    return fish_rest.tts(text, voice_id, out_path=out_path, speed=speed,
                         volume_db=volume_db, temperature=temperature)


# ---- request: pi/human asks to spend → human task queue (no direct spend)

def audio_request(kind: str, params: dict, brand: str = "sleepdraw",
                  db_path: str | None = None) -> dict:
    """Quote + freeze + queue. kind=speak|generate. Dry-runs server-side,
    stores the EXACT live payload in a review bundle, proposes an effect
    task (PROPOSED → REVIEW_READY). Human approves in dash queue; fulfill
    executes with a payload-bound grant. Never spends here."""
    try:
        from runtime import make_spec  # noqa: F401 (validates consequence)
    except ImportError:
        from pipeline.runtime import make_spec  # noqa: F401
    try:
        from effects import create_bundle, propose, transition
    except ImportError:
        from pipeline.effects import create_bundle, propose, transition
    import os as _os
    _db = db_path or _os.environ.get(
        "DASH_DB", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                 "..", "dash", "influence.db"))
    if kind == "speak":
        dry = speak(str(params.get("text", "") or ""),
                    str(params.get("voice_id", "") or ""), dry_run=True)
        if not dry.get("ok"):
            return dry
        payload, quote = dry["payload"], dry["quote"]
        cost_note = {"credits": quote["credits"]}
    elif kind == "generate":
        dry = generate_media(str(params.get("kind", "image") or "image"),
                             str(params.get("workspace_id", "") or ""),
                             str(params.get("model_id", "") or ""),
                             str(params.get("prompt", "") or ""),
                             int(params.get("expected_credits", 0) or 0),
                             dry_run=True)
        if not dry.get("ok"):
            return dry
        payload = dry["payload"]
        cost_note = {"estimate": dry.get("estimate")}
    else:
        return {"ok": False, "reason": f"kind={kind}: use speak|generate "
                "(studio kinds go through the studio UI approve flow)"}
    b = create_bundle(f"audio.{kind}", brand, payload,
                      cost_estimate_usd=0.0,
                      consequence=cost_note, db_path=_db)
    t = propose(brand, f"audio.{kind}", b["id"], risk_class="low",
                cost_cap_usd=0.0, consequence=f"audio.{kind}", db_path=_db)
    transition(t["task_id"], "REVIEW_READY", by="audio.request", db_path=_db)
    return {"ok": True, "task_id": t["task_id"], "state": "REVIEW_READY",
            "payload_hash": b["payload_hash"], "quote": cost_note,
            "next": "human approves in dash queue → fulfill executes"}
