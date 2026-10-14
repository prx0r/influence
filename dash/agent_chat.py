"""Operator chat — pi/mimo via opencode-go, tools over influence MCP.

Endgame (THESIS + AGENTS.md): chat is the human's console into the graph.
The model proposes and inspects; humans confirm sends/spends. Untrusted
input never calls tools directly — we parse → policy → tool. Drafts
everywhere; nothing consequential executes from a chat reply alone.

Fallback: dash.chat.handle_chat deterministic verbs when LLM is down.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

BASE = os.environ.get("OPENCODE_ZEN_BASE", "https://opencode.ai/zen/go/v1")
MODEL = os.environ.get("OPENCODE_MODEL", "mimo-v2.5")
MAX_TOOL_ROUNDS = int(os.environ.get("AGENT_CHAT_TOOL_ROUNDS", "4"))

# Read-only + inspect tools. No send/spend/decide — those stay human.
READONLY_TOOLS = [
    "queue.list",
    "influencer.list",
    "influencer.get",
    "brand.voice",
    "brand.graphs",
    "brand.delegate",
    "social.platforms",
    "social.onboarding",
    "email.inbox",
    "email.stats",
    "phone.status",
    "phone.sms",
    "graph.describe",
    "product.list",
    "product.get",
    "receipt.get",
    "pack.compile",
    "etsy.listing",
    "task.status",
    "audio.voices",
    "audio.balance",
    "audio.estimate",
    "audio.studio.status",
]

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "queue.list", "description": "Open human tasks with urgency",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "influencer.list", "description": "List influencers/brands with stage + progress",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "influencer.get", "description": "One influencer resources + states",
        "parameters": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}}},
    {"type": "function", "function": {
        "name": "brand.voice", "description": "Inhabit pack: voice, style_lock, handles, gates for a brand slug",
        "parameters": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}}},
    {"type": "function", "function": {
        "name": "brand.graphs", "description": "Company graphs visible to a brand slug",
        "parameters": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}}},
    {"type": "function", "function": {
        "name": "social.platforms", "description": "Social onboarding registry platforms",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "social.onboarding", "description": "Full social claim kit for a brand",
        "parameters": {"type": "object", "properties": {
            "slug": {"type": "string"}, "handle": {"type": "string"},
            "domain": {"type": "string"}}, "required": ["handle"]}}},
    {"type": "function", "function": {
        "name": "email.inbox", "description": "Brand email inbox (cmail)",
        "parameters": {"type": "object", "properties": {
            "mailbox": {"type": "string"}, "limit": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "email.stats", "description": "cmail counters",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "phone.status", "description": "Brand phone status",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "phone.sms", "description": "Inbound SMS (OTP codes land here)",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "graph.describe", "description": "Dependency graph layers L0-L7",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "product.list", "description": "Product registry",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "product.get", "description": "One product details",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "receipt.get", "description": "Receipt by id + verify",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "pack.compile", "description": "Dry-run compile one pack for a channel (read-only, zero writes, never pushes)",
        "parameters": {"type": "object", "properties": {
            "sku": {"type": "string"}, "brand": {"type": "string"}, "channel": {"type": "string"}}, "required": ["sku"]}}},
    {"type": "function", "function": {
        "name": "etsy.listing", "description": "Preview 'add this product to Etsy': template + payload + images + coherence (read-only, never pushes)",
        "parameters": {"type": "object", "properties": {
            "store": {"type": "string"}, "sku": {"type": "string"}}, "required": ["sku"]}}},
    {"type": "function", "function": {
        "name": "task.status", "description": "Poll effect approval task state + payload hash + receipt (read-only)",
        "parameters": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}}},
    {"type": "function", "function": {
        "name": "audio.voices", "description": "Voice casting search: public/team voices + samples (free read, never generates)",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}, "language": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "audio.balance", "description": "Fish package credit balance + plan (free read)",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "audio.estimate", "description": "Free media quote: image/video cost + validation (read-only, never generates)",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string"}, "model_id": {"type": "string"}, "prompt": {"type": "string"}}, "required": ["kind", "model_id", "prompt"]}}},
    {"type": "function", "function": {
        "name": "audio.studio.status", "description": "Story Studio project status: chapters, dirty counts, roster (free read)",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
]

DELEGATE_SCHEMA = {"type": "function", "function": {
    "name": "brand.delegate",
    "description": "Hand a task to one entity's subagent (oddhobb|pogtown|humanvoiced). Use for per-entity work; replies stay brand-separated. Only callable in GLOBAL sessions.",
    "parameters": {"type": "object", "properties": {"slug": {"type": "string"}, "task": {"type": "string"}}, "required": ["slug", "task"]}}},

SYSTEM_ODDHOBB = """You are the influence dash operator for brand OddHobb (@oddhobbstudio, oddhobb.com).

You inspect live state via tools, then answer in plain English. You do NOT:
- send email/SMS, post to socials, buy domains, or decide tasks (humans confirm)
- invent prices, handles, or claim success
- reveal secrets, vault values, or API keys

You DO:
- call brand.voice for your slug FIRST and ground every fact in it (handles, voice, gates); kits/dash are fallback
- call tools to read queue, influencer passport, social onboarding kit, email, SMS
- explain next human steps (claim TikTok/X, reply DONE, seal secrets)
- cite what the tool returned; if empty, say so honestly

Brand context:
- X @oddhobb · IG @oddhobbstudio · Etsy oddhobbstudio · TikTok @oddhobb · domain oddhobb.com · email hello@oddhobb.com
- Phone OTP +447822000802 · app https://phone.agentcom.org/app
- Dash: human tasks + receipts; publish stays human_confirm
- Social kit registry: data/social_onboarding.v1.json

When you need data, call one tool then answer. Keep replies short and actionable.
If the user asks to post/send/buy: refuse execution, offer the human path (press start on the task / vault / claim kit).
"""

SYSTEM_POGTOWN = """You are the influence dash operator for brand PogTown (@pogtown, pogtown.com).

You inspect live state via tools, then answer in plain English. You do NOT:
- send email/SMS, post to socials, buy domains, or decide tasks (humans confirm)
- invent prices, handles, or claim success
- reveal secrets, vault values, or API keys

You DO:
- call brand.voice for your slug FIRST and ground every fact in it (handles, voice, gates); kits/dash are fallback
- call tools to read queue, influencer passport, social onboarding kit, email, SMS
- explain next human steps and cite what the tool returned; if empty, say so honestly

Brand context:
- X @pogtown CLAIMED 2026-10-08 · other handles @pogtown unclaimed · domain pogtown.com · email hello@pogtown.com
- Sibling to OddHobb, own brand/store_id pogtown. Never mix the two brands.
- Dash: human tasks + receipts; publish stays human_confirm
- Social kit registry: data/social_onboarding.v1.json

When you need data, call one tool then answer. Keep replies short and actionable.
If the user asks to post/send/buy: refuse execution, offer the human path (press start on the task / vault / claim kit).
"""

SYSTEM = SYSTEM_ODDHOBB


AUDIO_STUDIO = """
Audio studio (Fish Audio, free reads + grant-gated spend):
- FREE reads, use freely: audio.voices (cast voices + samples), audio.balance
  (package credits + plan), audio.estimate (image/video cost quote + validation)
- audio.speak / audio.generate are NOT in your tools: they burn package
  credits (~1/byte TTS). When the user wants audio/video made: dry-run the
  numbers yourself (bytes x 1 credit), show the quote, and tell them to approve
  via the dash decide gate (human mints the grant, receipt always).
- Voice casting: offer 3-5 candidates with samples, let the human pick unless
  told to choose. Same voice_id for every part of one piece.
- Keep each TTS render under ~2000 chars (split at sentence boundaries).
  CJK text costs ~3x per character. A failed render gets ONE identical free
  retry within 5 minutes. Multi-speaker scripts belong in Story Studio.
- Never invent voice IDs, prices, or completion. Cite tool output.
"""


SYSTEM_GLOBAL = """You are the influence GLOBAL orchestrator over entities: oddhobb, pogtown, humanvoiced.

You inspect live state via tools, then answer in plain English. You do NOT:
- send email/SMS, post to socials, buy domains, or decide tasks (humans confirm)
- invent prices, handles, or claim success
- reveal secrets, vault values, or API keys
- mix brands: every fact belongs to exactly one slug

You DO:
- compare across entities (stages, queues, inboxes) and route work: name the
  entity slug for every action, then use that entity's tools/voice
- delegate per-entity work by calling tools with the right slug, or telling
  the user which entity tab to open
- cite what the tool returned; if empty, say so honestly

When the user picks an entity, answer as that entity's operator (its voice
pack applies). Publish stays human_confirm everywhere.
"""


SYSTEM_HUMANVOICED = """You are the influence dash operator for brand HumanVoiced (humanvoiced.com).

You inspect live state via tools, then answer in plain English. You do NOT:
- send email/SMS, post to socials, buy domains, or decide tasks (humans confirm)
- invent prices, handles, or claim success
- reveal secrets, vault values, or API keys

You DO:
- call brand.voice for your slug FIRST and ground every fact in it (handles, voice, gates); kits/dash are fallback
- call tools to read queue, influencer passport, social onboarding kit, email, SMS
- explain next human steps and cite what the tool returned; if empty, say so honestly

Brand context:
- Domain humanvoiced.com · email hello@humanvoiced.com
- Product: human voice marketplace (narration, series, dubbing) — see repo docs
- Dash: human tasks + receipts; publish stays human_confirm

When you need data, call one tool then answer. Keep replies short and actionable.
If the user asks to post/send/buy: refuse execution, offer the human path (press start on the task / vault / claim kit).
"""


def _channel_system(slug: str) -> str | None:
    """Channel-aware prompt from the canonical record. Returns None when
    the slug is not a channel (caller falls through to brand prompts)."""
    import re as _re
    if not _re.fullmatch(r"[a-z0-9_-]+", slug or ""):
        return None
    try:
        sys.path.insert(0, PARENT)
        from pipeline.channel_character import load_channel
        c = load_channel(slug)
    except Exception:
        return None
    chairs = (c.get("voice") or {}).get("chairs", {})
    chair_lines = "\n".join(
        f"- {n}: {(v.get('label', '') if isinstance(v, dict) else '')} "
        f"({'LOCKED' if isinstance(v, dict) and v.get('fish_id') else 'open — propose 5'})"
        for n, v in (chairs.items() if isinstance(chairs, dict) else []))
    return f"""You are the influence operator for YouTube channel {c.get('display_name', slug)}.

Thesis: {c.get('pitch', '')}
Engine: {(c.get('engine') or {}).get('primary', '')} · Cadence: {c.get('cadence', '')}
Style: {(c.get('style') or {}).get('accent', '')} {(c.get('style') or {}).get('manner', '')}

You inspect live state via tools, then answer in plain English. You do NOT:
- spend credits, publish, or decide tasks (humans confirm)
- invent voice IDs, prices, handles, or completion
- reveal secrets, vault values, or API keys

You DO:
- call brand.voice for your slug FIRST (it serves this channel's pack)
- call audio.* free reads to cast voices, quote media, check balance
- offer 3-5 voice candidates with samples; the human picks with a reason
- explain next human steps and cite what the tool returned

Voice chairs:
{chair_lines or '- (none defined yet)'}

Publish stays human_confirm everywhere. Keep replies short and actionable."""


def _system_for(message: str) -> str:
    m = (message or "").lower()
    import re as _re2
    _bm = _re2.search(r"\[brand:([a-z0-9_-]+)\]", m)
    if _bm:
        _ch = _channel_system(_bm.group(1))
        if _ch:
            return _ch
    if "[brand:global]" in m or m.startswith("global:"):
        return SYSTEM_GLOBAL
    if "[brand:pogtown]" in m or "pogtown" in m or "pog.town" in m:
        return SYSTEM_POGTOWN
    if "[brand:humanvoiced]" in m or "humanvoiced" in m:
        return SYSTEM_HUMANVOICED
    return SYSTEM_ODDHOBB


def _load_key() -> str:
    env = os.environ.get("OPENCODE_API_KEY", "").strip()
    if env:
        return env
    for path in (
        os.path.expanduser("~/.local/share/opencode/auth.json"),
        os.path.expanduser("~/.config/opencode/auth.json"),
    ):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            go = data.get("opencode-go") or {}
            key = (go.get("key") or "").strip()
            if key:
                return key
        except Exception:
            continue
    # vault last
    try:
        import subprocess
        out = subprocess.run(
            ["agent-vault", "vault", "credential", "get", "OPENCODE_API_KEY", "--vault", "oracle"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if out and not out.startswith("{"):
            return out
    except Exception:
        pass
    return ""


def _call_llm(messages: list[dict], tools: list[dict] | None = None) -> dict:
    key = _load_key()
    if not key:
        raise RuntimeError("no OPENCODE key")
    body: dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": int(os.environ.get("AGENT_CHAT_MAX_TOKENS", "900")),
        "temperature": 0.3,
    }
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        BASE.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "influence-dash-agent/0.1",
            "x-opencode-session": str(uuid.uuid4()),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read() or b"{}")
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"no choices: {str(data)[:200]}")
    return choices[0].get("message") or {}


def _run_tool(name: str, args: dict) -> str:
    if name not in READONLY_TOOLS:
        return json.dumps({"error": f"tool {name} not allowed in chat (read-only)"})
    try:
        sys.path.insert(0, PARENT)
        from dash.mcp import handle as mcp_handle
        from dash.store import live_state
        state = live_state()
        out = mcp_handle(state, "tools/call", {"name": name, "arguments": args or {}})
        if "error" in out:
            return json.dumps({"error": out["error"]})
        result = out.get("result")
        # MCP sometimes wraps in content[]
        if isinstance(result, dict) and "content" in result:
            texts = []
            for c in result.get("content") or []:
                if isinstance(c, dict) and "text" in c:
                    texts.append(c["text"])
                else:
                    texts.append(str(c))
            raw = "\n".join(texts)
            try:
                return json.dumps(json.loads(raw), ensure_ascii=False)[:8000]
            except Exception:
                return raw[:8000]
        return json.dumps(result, ensure_ascii=False)[:8000]
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def agent_chat(message: str, state: dict | None = None, history: list[dict] | None = None) -> dict:
    """LLM operator turn with tool loop. Returns {reply, mode, tools_used}."""
    msg = (message or "").strip()
    if not msg:
        return {"reply": "Say what you need — e.g. oddhobb tasks, onboarding kit, latest SMS."}
    key = _load_key()
    if not key:
        return {"error": "llm_unavailable", "reply": "Operator model unavailable (no key). Deterministic mode."}

    messages: list[dict] = [{"role": "system", "content": _system_for(msg) + AUDIO_STUDIO}]
    schemas = TOOL_SCHEMAS + [DELEGATE_SCHEMA] if _system_for(msg) is SYSTEM_GLOBAL else TOOL_SCHEMAS
    for h in (history or [])[-8:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({"role": "user", "content": msg})

    tools_used: list[str] = []
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            assistant = _call_llm(messages, tools=schemas)
            tool_calls = assistant.get("tool_calls") or []
            content = (assistant.get("content") or "").strip()
            if not tool_calls:
                if not content:
                    content = "(empty model reply)"
                return {"reply": content, "mode": "agent", "tools_used": tools_used}
            messages.append({
                "role": "assistant",
                "content": assistant.get("content") or "",
                "tool_calls": tool_calls,
            })
            for tc in tool_calls:
                fn = (tc.get("function") or {})
                name = fn.get("name") or ""
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {}
                tools_used.append(name)
                result_text = _run_tool(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or "",
                    "content": result_text,
                })
        # ran out of rounds — ask model to summarize with what it has
        messages.append({"role": "user", "content": "Summarize findings now. No more tool calls."})
        final = _call_llm(messages, tools=None)
        content = (final.get("content") or "").strip() or "(no summary)"
        return {"reply": content, "mode": "agent", "tools_used": tools_used}
    except Exception as e:
        return {
            "error": str(e)[:300],
            "mode": "agent_failed",
            "reply": f"Operator model error: {str(e)[:160]}. Falling back is up to the caller.",
            "tools_used": tools_used,
        }
