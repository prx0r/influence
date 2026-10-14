# Cloudflare: Workers AI + R2 — exact usage (for the other agent)

Copy-paste contract. Canonical code: `pipeline/providers/cloudflare.py`
(images), `pipeline/r2_presign.py` (reads), `scripts/ship_audio.py`
(writes), `/root/sleepdraw/sleepdraw/art.py` (proven first user).

## Workers AI (image generation, $0 free allocation)

- Endpoint: `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/ai/run/{MODEL}`
  with `Authorization: Bearer {TOKEN}`, JSON body.
- Models (keys in `MODEL_IDS`): `flux` → `@cf/black-forest-labs/flux-1-schnell`
  (default), `sdxl`, `lightning`, `dreamshaper`. Unknown key raises —
  never guess a model string.
- Body: `{"prompt": "..."}` (+ optional `num_steps`). Nothing else.
- Auth order: vault oracle `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_WORKERS_TOKEN`,
  fallback `CLOUDFLARE_API_TOKEN`. Read at call time via
  `agent-vault vault credential get <KEY> --vault oracle`. NEVER in tree,
  NEVER in code, NEVER printed. Empty creds → fail closed, do not retry.
- Response handling (BOTH shapes, this is where people break):
  1. `Content-Type: image/*` → body IS the bytes, return as-is.
  2. JSON → `json["result"]["image"]` is base64 → `base64.b64decode`.
- Retry: 4 tries, 15s sleep, 180s timeout. Return last error (≤200 chars).
  Callers (never this module) own grants: live runs go through
  `pipeline/runtime.py:execute()` with consequence `generate_paid`.
  Cost logged as $0.00 — still receipted.
- Proven: flux stills (Yuki doorway 208KB), flux 1MB + sdxl 2MB test renders.

## R2 (private audio/object archive, negligible cost)

- S3-compatible endpoint from vault `CLOUDFLARE_R2_ENDPOINT` (+
  `CLOUDFLARE_R2_ACCESS_KEY` / `..._SECRET_KEY`). Account `954612af…`.
- Bucket: `blog-video-assets`. Key layout: `audio/<channel>/<file>.mp3`
  (see `r2_presign.audio_key` — sanitizes, 120-char cap).
- Writes (`scripts/ship_audio.py`, needs boto3 — system python ONLY,
  dash venv lacks it): single-PUT `put_object` with `ContentType`,
  then `head_object` size check, then write `r2_key`+`r2_bucket` into the
  sidecar `.json`, then delete local. Never delete before HEAD verifies.
  Policy: masters + clips older than 3 days; playback stays working.
- Reads: bucket is PRIVATE (no public URL — outputs.moltwork.com 403s on
  keys, r2.dev host is wrong; do not waste time on either). Playback =
  presigned GET (`pipeline/r2_presign.py`, stdlib SigV4, 1h expiry):
  dash `/api/studio/file?kind=voice` 302s there when local is pruned.
  Verified: full 1.1MB master fetched through the chain.
- Bank lists archived clips from sidecar metas (`r2_key` present, mp3
  absent) with R2 badges. Do not "clean up" sidecars — they ARE the index.

## Don't

- Don't add models without proving them live first ($0 test render).
- Don't store creds anywhere except vault oracle.
- Don't make the bucket public to "simplify playback" — presigned URLs
  are the design.
- Don't run ship with `--days 0` unless the owner explicitly asks
  (it archives everything including today's work).
