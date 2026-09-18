# Sparky setup skill — onboard one trade business in ~15 minutes

Run these steps with the operator (Muse Code / Claude / human). Verify each
before moving on. The number to watch at the end: qualify→survey conversion.

## 1. Clone the kernel (2 min)
```bash
cp stevejobless/knowledge/sparky_electrician_en.yaml stevejobless/knowledge/<biz>_en.yaml
```
Edit `business:` (name, phone, hours), `tradie.price_book` (labour per job
type), `tradie.preferences` (slots, max distance, min value, affinities).
Same file drives the voice agent as `BUSINESS_CONFIG` — do not fork it.

## 2. Register + load (1 min)
Add the project row (slug `<biz>`), then:
```bash
curl -X PUT localhost:8787/api/tradie/<biz>/kernel -H 'content-type: application/json' -d @kernel.json
```
where `kernel.json` is the `tradie:` block as JSON. Check:
`GET /api/tradie/<biz>/kernel` shows your price book.

## 3. Autonomy + retention (1 min)
Default `autonomy: observe` (log only). Move to `semi_auto` (auto-draft
quotes) when quotes look right; `full_auto` (propose slots) later.
Sends ALWAYS need tradie confirm. Default transcript retention 90d:
`POST /api/tradie/<biz>/sweep` needs `confirm:true` — run it quarterly.

## 4. Connect WhatsApp (5 min)
Meta dashboard → WhatsApp Cloud API → app + test number. Set:
```
WHATSAPP_TOKEN=… WHATSAPP_PHONE_NUMBER_ID=… WHATSAPP_VERIFY_TOKEN=<random>
```
Verify: `GET /api/tradie/whatsapp/webhook?hub_verify_token=<random>` → challenge.
Send a test message → new job appears in `GET /api/tradie/<biz>/jobs`.

## 4b. Backend: Telnyx + LiveKit + Google (10 min, agent-managed)
```bash
POST /api/backend/<biz>/telnyx/credential {"api_key":"…"}
GET  /api/backend/<biz>/telnyx/numbers            # pick a number
POST /api/backend/<biz>/telnyx/wire {"connection_id":"…","phone_number":"+44…","base_url":"https://steve…"}
GET  /api/backend/<biz>/livekit/sip-config        # hand this JSON to the voice agent
POST /api/backend/<biz>/gcal/auth-url {...}       # tradie opens URL, pastes code:
POST /api/backend/<biz>/gcal/callback {"code":"…"}
POST /api/backend/<biz>/gcal/calendar {"calendar_id":"primary"}
```
Then `POST /api/tradie/<biz>/reconcile` — every backend row must read READY
(or an honest MISSING with the next step). Secrets live in the encrypted
vault, never in the kernel. Completed calls land as jobs via the voice
webhook automatically; SMS confirm degrades to logged stub without creds.

## 5. Connect the voice side (3 min)
Voice agent gets: intake URL, kernel YAML path, `docs/VOICE_COMPAT.md`.
Place a test after-hours call → job + transcript + action appear; urgent →
priority-100 wake-now. Read the quote preview back to the caller.

## 6. Verify first job end-to-end (3 min)
intake → quote (£ maths vs price book) → confirm slot → done with
final_price + duration_min → stats move. If qualify→survey < 40%, trim the
photo ask to 2 photos in the kernel FAQ node.

## Traps
- Never invent prices: unknown job types quote a site visit + human review.
- Never auto-send: drafts + explicit confirm, any autonomy level.
- Transcripts have a TTL: the sweeper deletes messages, never job metadata.
- AGPL repos (AIReceptionist, sara): patterns only, never paste code.

## 7. Domains: check → buy → wire (agent-run, human-confirms-spend)
```bash
GET  /api/domains/check?domain=x.dev&provider=porkbun   # checker prefilter + live price
POST /api/domains/prepare {"domain":"x.dev","max_price":25,"registrant_email":"…"}
POST /api/domains/{id}/approve                          # one-time token out
POST /api/domains/{id}/register {"approval_token":"…"}  # rechecks price first
POST /api/domains/{id}/wire?worker=cmail                # CF zone → NS → routing → business
```
Sandbox/default-deny: Porkbun sandbox + name.com dev until `DOMAINS_ALLOW_LIVE=1`.
Price drift >10% or over budget aborts with a receipt. Name.com needs manual
NS change (no NS API); Porkbun does it via API.
