# Media pipeline — target state (2026-10-14, for peer review)

Voice pilot approved → title + thumbnail auto → images → sleepdraw video
assembly → R2 → upload package. $0 default; paid paths grant-gated and
mostly stubbed pending keys.

## Stage map

```
[voice pilot approved (bank master)]
        │
        ├─► titles: recipe (sleepintel steals + easy package) + tale metadata
        │         → candidate titles → human picks (config UI)
        │
        ├─► thumbnail still: art frame (sleepdraw/CF) + PIL text overlay
        │         → 1280x720 JPEG ≤2MB → human picks
        │
        ├─► images: provider router (pipeline/providers/)
        │     NOW:  cloudflare Workers AI flux/sdxl — $0, LIVE (vault creds)
        │     LATER: fal (stub, fails closed) — needs FAL_KEY in vault
        │     LATER: fal MCP (not configured) — needs key + opencode entry
        │
        ├─► video assembly (prx0r/sleepdraw, /root/sleepdraw/sleepdraw/):
        │     art.py (FLUX stills) → draw.py (slow-stroke render, lora1/2)
        │     → sequence.py (chain + fades) → mux with narration master
        │     → ship.py (R2 powoutputs/films/, recipe JSON)
        │     Status: PROVEN standalone (moon v4, Corbin shots 1-4).
        │     Wire-in: pass our bank master.mp3 + chapter marks as the
        │     audio track; read back mp4 + recipe into our vault.
        │
        └─► upload package: title + desc + tags + thumb + end screen
              (powvid shorts/upload.py thumbnails().set — needs per-channel
              OAuth, human step; unlisted-first law holds)
```

## Per-stage contract

| Stage | Input | Output | Cost NOW | Gate |
|---|---|---|---|---|
| voice pilot | drama.txt / readout | bank master.mp3 + receipt | $0 | prep≥70 + gate + poison |
| titles | tale metadata + recipe | 3 candidates | $0 | human picks 1 |
| thumb still | art frame + title text | 1280x720 ≤2MB | $0 (CF) | human picks 1 |
| images | prompt + channel style | art plates | $0 (CF) / fal later | grant only if paid |
| video assembly | stills + master.mp3 | final.mp4 + recipe | $0 compute | human review |
| R2 ship | final.mp3/mp4 | `audio/` + `powoutputs/films/` keys | ~$0 | verify HEAD, prune local |
| upload | package + OAuth | unlisted video + thumb | 50u thumb | human flips public |

## Blockers (human inputs, in order)

1. **FAL_KEY in vault oracle** — unlocks fal provider + fal MCP config.
   Nothing fal-shaped runs until then (stubs fail closed by design).
2. **Per-channel Google OAuth** — upload + thumbnails.set per channel.
3. **Voice locks** (ongoing) — narrator + chairs per channel.

## Laws (unchanged)

- $0-first: free tier for tests/casting/snippets/bulk; credits only on
  explicit owner yes per item (kill-switch: CREDIT_SPEND_ENABLED).
- Verbatim P0: read the book; no retells without per-item approval.
- One voice per project, never shared. Differentiation = persona + ritual.
- Receipts for everything; bank metas carry voice/knobs/source.
- Secrets in vault/env, never in tree (secret-scan before push).
