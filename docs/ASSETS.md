# Assets — where everything lives (2026-10-14)

One rule: every artifact carries its provenance (source path + voice +
knobs + recipe). No orphan files.

## Live map

| What | Where | Format | Lifecycle |
|---|---|---|---|
| Tale scripts | `damn/projects/<house>/{pilots,videos,readout}/` | `.drama.txt` / `.read.txt` + `//` headers | permanent, versioned in damn |
| Source books | `easy/folk-and-fable/*/source.txt` | Gutenberg text | permanent |
| Voice clips + snippets | sleepdraw bank (`runs/studio/voice/`) | MP3 + sidecar `.json` meta | 3 days local → R2 `audio/<channel>/`, presigned playback |
| Masters (pilots/episodes) | bank, then R2 `audio/<channel>/` | MP3 + receipt meta | same lifecycle |
| Art stills | `sleepdraw/assets/` + `runs/studio/art/` | JPG | permanent (small) |
| Etch renders | `sleepdraw/runs/studio/renders/` | MP4 intermediates (mpeg4!) | scratch — finals only survive |
| Thumbnails | `pipeline/runs/<channel>/thumbs/` | 1280x720 JPEG ≤2MB | permanent w/ video |
| Films (finals) | R2 `powoutputs/films/<film>/` + recipe JSON | MP4 (YT-normalized, below) | permanent, R2-first |
| Video records | bgraph `registry/content/items/<id>.json` | JSON | permanent, validated |
| Channel records | influence `studio/channels/<slug>.json` | JSON | permanent |

## Per-video vault (new finals follow powvid pattern)

`videos/<VIDEO-ID>/`: script.txt + facts + theme + storyboard + voices
(+IDs) + art/ + thumb.jpg + master.mp3 + final.mp4 + manifest.json
(hash-pinned) + receipt. One folder = full reproducibility.

## Final mux spec (YT-normalized — ALWAYS re-encode, never copy)

Etch intermediates are mpeg4/odd sizes. Finals:

```
ffmpeg -i <etch.mp4> -i <master.mp3> \
  -vf "scale=1920:1080,format=yuv420p" \
  -c:v libx264 -preset veryfast -crf 23 \
  -c:a aac -b:a 128k -ar 48000 -shortest \
  -movflags +faststart <final>.mp4
```

Then `yt_compliance.check_package()` gates before any upload quota burns.

## FableCut verdict (evaluated, not adopted yet)

FableCut (browser NLE, project.json timeline, MCP/REST, `root/fablecut`)
fits as the **edit-decision layer**: our assembler would emit
`project.json` (narration track + stills + bed + captions) instead of raw
ffmpeg commands — auditable, human-tweakable in browser, agents can edit.
ffmpeg still renders. NOT running its server now (needs node + operator):
adopt when human timeline tweaks become the bottleneck (post-first-uploads).
No code dependency added; no MCP configured.

## fal status

Key vaulted (`FAL_KEY`, oracle). Provider live but double-gated (grant +
`FAL_SPEND_ENABLED`, both off). Router default stays Cloudflare-free.
Video gen (Kling/Seedance) unlocks on owner spend approval per job.
