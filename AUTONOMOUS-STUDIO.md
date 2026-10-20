# AUTONOMOUS STUDIO — three layers, hard seams

> START HERE. This file is the map. RUNTIME.md (per channel) is the factory
> manual. PACK-FORMAT.md is the pack spec. `channel.skill` serves any
> channel's full skill pack over MCP. New agent? Read this file, then the
> channel's RUNTIME, then run.

## Doc map (single source of truth per row — no duplicates)

| Question | Answer lives in |
|---|---|
| What are the layers? | this file |
| How do I make a video for channel X? | `damn: projects/X/RUNTIME.md` (only folk-and-fable yet — copy it) |
| Why does channel X work? How is it styled? | `channel.skill X` (thesis + lane + style profile, live docs) |
| How do I write/direct TTS? | `damn: fish/` engine (`direct.py`, `normalize.py`, `validate.py`…) |
| What beats go in a video? | `damn: docs/video-structure.md` (universal 6 + lane overlay) |
| What's a vid pack vs MVP-0 pack? | `sleepdraw: pack/PACK-FORMAT.md` |
| Where do files live / how do packs move? | `sleepdraw: pack/R2-LAYOUT.md` + `pack/r2sync.sh` |
| Which tales → which uploadable? | `damn: projects/folk-and-fable/art/UPLOADABLES.md` |
| Per-tale images? | `damn: projects/folk-and-fable/art/cluster-*.spec.md` |
| Upload gates? | `influence: pipeline/compilers/youtube.py`, `pipeline/yt_compliance.py` |
| Feedback verdicts? | `influence: pipeline/feedback_tick.py` |
| QC: prose slop? | `damn: fish/slop.py` (MCP `qc.text`) — coherence/rhythm/NoSlop signal |
| QC: audio delivery? | `damn: fish/deliver.py` (MCP `qc.audio`) — WPM vs chair, pauses vs tags |
| QC: finished video? | `damn: fish/gate_pack.py` (MCP `fable.gate`) → receipt JSON |
| Gate numbers per channel? | `damn: projects/<slug>/GATES.md` (U1–U5 + channel rows) |
| Unattended production? | `sleepdraw: pack/overnight.sh` (queue→build→gate→push; stops at human gates) |
| MCP surface? | `influence: dash/mcp.py` + `dash/fable_ops.py`; stdio bridge `dash/fable-mcp-stdio.py` |

## Exposure map (disk → MCP, audited 2026-10-20 — 85 tools, all live-called)
Everything useful on disk that agents need is a tool; the rest has a reason:

| Disk asset | MCP | Notes |
|---|---|---|
| damn fish engine (normalize/validate/gate/poison) | `qc.validate`, `qc.text` | pre-render FAIL-closed |
| damn slop + NoSlop signal | `qc.text` | suggested edits included |
| damn deliver | `qc.audio` | WPM + pauses vs tags |
| damn gate_pack | `fable.gate` | receipt JSON per video |
| damn direct.py (A/B/C direction) | `engine.direct` | $0, body untouched |
| damn mvp.py (content packs) | `engine.mvp` | $0 text-only |
| damn content.py (queue→receipt) | `engine.content` | dry-run default |
| damn books.py (PD finder) | `engine.books` | Gutendex→OL→GB |
| damn readout/diary/gate internals | via qc.* | composed, not raw |
| vid packs + R2 factory | `fable.*`, `r2.ls` | pull/build/gate/push |
| compilers/youtube.py | `release.compile` | dry-run payload+hashes |
| yt_compliance | inside `fable.gate` + compile | |
| feedback_tick | `feedback.tick` | needs Analytics OAuth for AVD later |
| analytics pull | `feedback.tick` internals | vault key read |
| voice bank (170 masters) | `studio.voicebank` | ids per file |
| channel skills/thesis/lanes/styles | `channel.skill` | live docs |
| voice registry + pick protocol | inside `channel.skill` | registry.md served |
| skills (find-voices, render-episodes, motion-probe, earshot-qc, fish-voices, laptop-anatomy) | `skill.get` | |
| morning review + fix-queues + content queues | `status.morning` | |
| overnight cron + queue + log | `status.overnight` | |
| sleepvids section sources | via qc.text paths | project-relative reads |
| gcomedy attardo graph (76n/117e) | — | comedy-theory knowledge; park until a comedy channel needs it |
| characters2 jokegate/jev delivery | — | comedy-specific; determinists already ported (slop/deliver); Jev loop stays on its repo |
| sleepdraw board/shot CLI (corbin film machine) | — | corbin-specific; studio.* covers art/etch for channels |
| earshot (audio critique) | — | proven skill, needs model pull; wire when foley QC matters |
| Go/Opencode keys, FAL, OAuth | — | spend/credentials; human-gated by law, never tools |

## Running the studio server
`dash/launch-8795.sh` (sets LIVE=1 YT_MODE=1, port 8795 — the tunnel target
for youtube.agentcom.org). Rebuilt venv: `stevejobless/.venv` via `uv sync`.
Restart picks up `mcp.py`/`fable_ops.py` changes (modules cache on import).

`youtube.agentcom.org` is one studio with three separated layers. Data flows
one way through gates; feedback returns as rows, never as edits. No layer
reaches into another's internals — only across the contracts below.

```
L1 CREATION ............ finished MP4 + thumb + manifest + hashes
  → L2 UPLOAD .......... videoId + publish receipt
    → L3 FEEDBACK ....... verdicts + re-ranked queue → back to L1
```

## L1 — CREATION (make videos, never publish)
Owns: everything before a finished file exists.
- damn routines 01–07 (cast/drama/voice/sfx/bed/visual/ship) + house laws
- style bibles, tableau specs (`art/cluster-*.spec.md`), pack format
- vid packs (`runs/studio/packs/`, `pack/build_packs.py`, `pack/build.sh`)
- R2 factory transport (`pack/r2sync.sh`, `pack/R2-LAYOUT.md`)
- sleepdraw engine (art → etch → render), `dash/sleep_studio.py`
- pilot loop (`dash/yt_studio.py`: pilot → preview → re-take → render → formula)
- MCP: `channel.*`, `fable.*` (build/still/packs), `studio.*`, `audio.*`
- OUTPUT CONTRACT (to L2): `<slug>-full.mp4` (1080p24 h264+aac, -14 LUFS,
  faststart) + `thumb.jpg` (1280x720 ≤2MB) + `upload-manifest.json`
  (title/desc/tags/chapters) + sha256 of each. Nothing else crosses the seam.

## L2 — UPLOAD (gates + release, never creates)
Owns: everything between a finished file and a public video. NEVER edits
pixels, audio, or metadata — only checks hashes and files paperwork.
- `pipeline/release.py` — ChannelRelease: pins pack hash + payload hash;
  humans approve the hash; executors check the hash (youtube: LISTABLE —
  already registered as a channel).
- `pipeline/compilers/youtube.py` — release → videos.insert payload
  (title/desc/tags/chapters/privacy) + thumbnails.set. Dry-run default.
- `pipeline/yt_compliance.py` — ffprobe + metadata gate BEFORE quota burns.
- `pipeline/gates/human_confirm.py` + `pipeline/scheduler.py` — queue only
  after gate pass; fire only after human approval.
- MCP: `yt.upload` = DRAFT ONLY (stages manifest, returns gates).
- OUTPUT CONTRACT (to L3): videoId + publish timestamp + receipt row.
  UPLOAD NEVER RUNS without: compliance PASS + human_confirm + OAuth creds
  (which do not exist on this box yet — executor stays code-gated).

## L3 — FEEDBACK (numbers back, kill/continue, never vibes)
Owns: everything after publish. Writes verdict rows; L1 reads them as queue
order. Never touches content, only ranks it.
- `pipeline/analytics.py` — `youtube_channel()` (channel stats) +
  per-video stats pull (views/likes/comments) via vault YOUTUBE_API_KEY.
  Read-only, already live.
- `pipeline/channel_state.py` — `record_metrics`, `can_publish`,
  `record_post`, cooldowns. The ledger L3 writes to.
- Verdict evaluator (tick): per-video stats vs gates —
  pilot gate (AVD >40% unlisted), CTR floor, night-two retention,
  completion. PASS → etch chain + series order; FAIL → kill, reason logged.
- MCP: `yt.analyze/list/get/compare` (intel), verdict rows via actions ledger.
- OUTPUT CONTRACT (to L1): verdict rows {videoId, metric, gate, pass/fail,
  action} + re-ranked creation queue. L1's next batch order COMES FROM HERE.

## The loop, end to end (folk-and-fable pilot as example)
1. L1: Yuki pack → stills → `./build.sh` → final + thumb + manifest (+ hashes)
2. L2: compliance PASS → ChannelRelease pinned → human approves hash →
   executor uploads unlisted → videoId + receipt
3. L3: tick pulls video stats → AVD vs 40% gate → verdict row →
   PASS: etch chain + Snow Queen next; FAIL: kill with reason, next tale up
4. Owner sees one queue: drafts → awaiting-approval → live → verdicts.

## Missing glue (in build order)
1. ~~`pipeline/compilers/youtube.py`~~ DONE (dry-run; caught a real
   yuvj420p defect in the practice render — build.sh fixed + packs rebuilt).
2. Upload executor — code-gated until OAuth creds exist (owner). Manifest
   staging via `yt.upload` draft tool works now.
3. ~~Feedback tick~~ DONE as `pipeline/feedback_tick.py` (synthetic-verified;
   live pull on first real publish). Cron scheduling still open.
4. MCP surface: 11 new tools live on the studio (`channel.*`, `fable.*`,
   `r2.ls`, `yt.upload`) + `dash/fable-mcp-stdio.py` stdio bridge for
   opencode/Claude. 71 tools total.
