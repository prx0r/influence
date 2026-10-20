# AGENTS.md — binding rules for coding agents working in this repo

1. **NO EXTERNAL CONSEQUENCE OUTSIDE THE EFFECT RUNTIME.** Anything that
   spends, publishes, sends, buys, mutates a listing, launches an ad,
   generates paid media, or orders goods MUST go through
   `pipeline/runtime.py:execute()` with a verified qprivately grant.
   Direct adapter calls fail closed. CI enforces this (see `runtime.guard_imports`).
2. **Untrusted input stays untrusted.** Email/DM/voice content never calls tools
   directly. Parse → classify → policy → tool. Quarantine can only downgrade.
3. **Drafts everywhere; sends need explicit human confirm** — at every autonomy
   level, no exceptions. A `send` that didn't happen must report `sent:false`.
4. **Money moves need approval tokens** (single-use, sha256-stored) + fresh
   rechecks (availability, price drift ≤10%, budget cap). Fail closed, receipt everything.
5. **No blind buys, no invented prices.** Unknown job types quote a site visit.
   Missing prices refuse, never estimate silently.
6. **Secrets in vaults/env, never in the tree.** Secret-scan before every push:
   `grep -rIlE "cfat_|ghp_|sk-[A-Za-z0-9]{10,}" --exclude-dir=node_modules --exclude-dir=.venv .`
7. **AGPL is patterns-only.** Read, reimplement cleanly, never paste. (MIT/Apache may be vendored with attribution.)
8. **Additive changes to live surfaces.** The checker site and cmail worker serve
   real traffic: never rename/remove a route or MCP tool; add alongside.
9. **Prove it live.** New backend code ships with: unit tests, a live check
   against real infra, and a receipt in the summary. "Works locally" isn't done.
10. **One kernel file, two consumers.** `stevejobless/knowledge/<biz>_en.yaml`
   drives voice `BUSINESS_CONFIG` and the brain kernel — copy, never fork.
11. **Keep the queue human-sized.** Wake-now is for emergencies. Everything else
    batches to morning. Alert fatigue is a security bug (see `docs/SECURITY.md`).
12. **youtube.agentcom.org is THE dash. agentcom.org is legacy — do not touch.**
    All studio/channel/voice/casting work ships to and is verified on the YT
    dash (:8795, YT_MODE=1). Never send the owner agentcom.org links for
    studio content. Verify with `curl https://youtube.agentcom.org/api/health`
    + the actual route before reporting live. Restart :8795 (not :8793) after
    backend changes; static files need no restart but hard-refresh to confirm.
13. **Owner law: 0 credits ever** (CREDIT_SPEND_ENABLED unset — kill-switch in
    `pipeline/audio_flow.py`). Free tier only until the owner explicitly says
    otherwise. No workarounds, no exceptions, no "just this once".
    - **APIs are in .env files you can read** (key names only, never print or
      commit values): `/root/influence/.env` (YOUTUBE_DATA_API_KEY),
      `/root/characters/audition/.env` (FISH_API_KEY, 600, gitignored),
      `~/.config/influence/fish-mcp.json` (Fish MCP OAuth, independent refresh).
      `fish_rest.py` reads them in that order. `/root/.fish-env` is MISSING
      by design (damn direct client errors; influence path is fine).
    - **Fish MCP: connect, spend $0.** Free reads only — `balance` / `voices` /
      `voice_detail` / `estimate_*` / `studio import/status` (no grant needed).
      Anything billed (`speak` / `studio_generate` / `studio_export` /
      `generate_media`) fails closed without a grant AND without
      CREDIT_SPEND_ENABLED=1. Dry-run first, queue via `audio_request`, human
      approves in dash — never call billed tools direct.
    - **All rendering is fish free-pro API ONLY** (`s2.1-pro-free` via
      `pipeline/providers/fish_rest.py` → `audio_flow.speak_free()` → dash
      `render_pilot` / `free_narrate`). Same pro quality, $0, fair-use.
      Paid models (`s2.1-pro`, voice-design $0.01, MCP `text_to_speech`) are
      NEVER a render path — `fish_rest.tts()` raises on non-free models by
      construction. If it isn't `speak_free`, it isn't rendering.
14. **URL map (read before touching any frontend):**
    - `youtube.agentcom.org/studio` — THE STUDIO. Channel rail, Pilots
      (preview/full/formula), Voices (casting grid), Thumbnail + Titles
      templates, Formats, pinned Pi bar. Owner's daily surface. Served from
      `dash/static/yt.html` by the :8795 process (YT_MODE=1).
    - `youtube.agentcom.org/` and `/classic` — FULL CONSOLE on the YT box.
      Same backend as the studio plus queue, receipts, chat, explorer,
      monitor, review canvas. Debug here, live here when the studio lacks
      a control. Served from `dash/static/index.html`.
    - `agentcom.org` — LEGACY commerce dash (:8793, oddhobb/Etsy/phone
      queue). Working system, different lane. Do not repurpose, do not
      remove commerce surfaces, do not send studio links here.
    - `video.agentcom.org` / `image.agentcom.org` — embed-only iframes
      inside the console's studio tabs (ports 7777/7778, other owners).
      Never modify; never depend on their uptime for YT flows.
15. **Casting lane handover: `docs/HANDOVER-CASTING.md`.** Next agent starts
    there (engine map, open threads, never-dos). This rule is the link —
    keep the handover current when the lane changes hands.

## TOPOLOGY (how the three repos connect; full map: damn/AGENT-START-HERE.md)
- influence (you are here) = PLATFORM + hands: MCP tools, release, feedback, qp runtime. R2 creds load at runtime from /root/.r2-factory. Publish = draft + human hash, always.
- damn = CHANNELS + judgment: channel runtimes, fish gates, voice registry. Judges what passes; spends nothing.
- sleepdraw = WORKSHOP: packs, styles, voice runs, R2 transport (merge candidate → damn/production/).
- Flow: agent → this MCP (channel.skill serves damn) → engines (damn judges, sleepdraw builds) → R2 artifacts / damn receipts / influence state.
- Secrets in NO repo · timers in SYSTEM crontab only (02:00 factory, 09:00 scan) · absolute paths bind all three — rewrite before any move.
