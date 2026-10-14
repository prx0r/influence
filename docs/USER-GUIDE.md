# User guide — what you can do + what Pi can do (2026-10-14)

Everything here is live on https://youtube.agentcom.org ($0 unless stated).

## Pi (chat bar, bottom of every page)

Pi reads the channel record, calls tools, cites results, never spends.
Talk to the selected channel's agent by picking it on top first.

**Ask Pi things like:**

| You say | Pi does (tools) |
|---|---|
| "status" / "how's folk-and-fable" | `channel.status` — chairs, brief, bank, next action |
| "find 3 whisper voices for yuki" | `audio.voices` — candidates + samples + reasons |
| "prepare the cast for andersen-part-1" | `audio.cast.prepare` — ensemble briefs + $0 auditions each |
| "render this line with Adrian: ..." | `audio.speak_free` — $0 clip straight to bank |
| "what's my balance" | `audio.balance` — plan, credits, per-call budget |
| "quote a Kling video of X" | `audio.estimate` — free server-side price, no task created |
| "how much is this Studio project" | `audio.studio.status` — chapters, dirty counts, roster |
| "render this on the paid path" | `audio.request` — quotes + files a human approval task (never spends) |
| "start a Yuki video" | walks the pilot flow: prep → snippet → full → titles |

**Pi cannot:** spend credits, publish, lock voices (you lock, with reasons),
invent voice IDs/prices/completions, or see files outside its tools. If it
reports an error instead of retrying blind on paid paths — that's by design.

## Studio (youtube.agentcom.org/studio)

Channel rail left (16 channels, dots = saved formulas) → tabs:

- **Pilots** — 76 scripts grouped by house with READY dots (prep≥70 +
  gate + poison). ▶ Hear preview ($0 first segments, autoplay, space
  toggles). "Ok render full" = background job (no timeout). Knobs:
  pace / expression / volume / chair voices — retakes re-render free.
  Video workspace per pilot: ID, words/minutes, voice map, 3 title
  drafts (pick to save), thumb draft (pick to save), render button.
- **Voices** — casting grid: 5 candidates + samples + reasons + ✓/✗ +
  notes + hear-our-line ($0) + lock. "More like these" (fresh search),
  "ask pi" (prefilled brief), "design new voice" ($0.01, confirm first).
- **Thumbnail** — template + rules editor, saved to channel record.
- **Titles** — formula list editor; per-video picks train future drafts.
- **Formats** — per chair/format views with Ask Pi prompts.

## Casting view (🎙️ icon, same engine, grid layout)

Channel + chair pickers, 5-card grid, ticks/notes/dismissals saved to
taste files (excluded from future proposes), hear-our-line, lock with
reason. Loved voices (`/api/studio/onboard/love` or send IDs in chat)
weight all future rankings with your descriptors cited.

## Voice-design engine (P0, $0.01/req, approval-gated)

Channel record → instruction prompt (`/api/studio/cast/design` previews
free) → confirm dialog → candidates banked → lock. Anchor compiler
(`anchor_prompt`) blends loved voices into new prompts. Nothing generates
without your explicit yes.

## Bank + R2 (voice bank outputs, top of studio)

Every clip named, voiced, char-counted, playable inline. Masters + old
clips auto-archive to private R2 (`audio/<channel>/`, HEAD-verified,
local pruned after 3 days); playback 302s to presigned URLs. "Ship"
button previews then confirms. Disk stays ~2MB.

## Thumbnails + video assembly

`pipeline/thumb.py`: art + ≤3-word serif + gold rule → 1280x720 ≤2MB.
Sleepdraw etch (own venv for cv2) → `start_assemble` (stills + master →
YT-spec final: H.264/yuv420p/AAC/48k/faststart) → `yt_compliance` gates
(codec/res/audio/moov + title/desc/tags + thumb) before any upload quota.
Upload itself (videos.insert + thumbnails.set) waits on per-channel OAuth.

## Upload path (when ready)

Script → studio → unlisted (human approves task, fulfill executes with
payload-bound grant + receipt) → human flips public. Quota: ~6 videos/day
(insert 1600u + thumb 50u). Compliance gate runs first, always.

## Laws (hard)

0 credits ever (kill-switch, `CREDIT_SPEND_ENABLED` unset) · verbatim P0 ·
one voice per project · free tier default · receipts always · human locks,
picks, verdicts; automation does everything else.
