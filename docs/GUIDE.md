# GUIDE — operate the stack

Start here. Assumes the README bring-up is done. Base URLs below use the live
deployments; swap for localhost when developing.

- Brain: `https://steve.intelligentothers.xyz` (desk at `/desk`)
- Bus: `https://cmail.tradesprior.workers.dev` (inbox at `/ui/`)
- Checker: `https://domainnamechecker.tradesprior.workers.dev`

## Daily: the morning queue

1. Open `/desk`. Top section is wake-now alerts (priority ≥ 90, red).
2. Work open jobs: quote → send (confirm) → calendar → call → done → invoice.
3. Clear actions (`Mark done`). Check Backend section: every row should be
   READY or an honest MISSING with the next step printed beside it.
4. Domains row: open deals + renewals needing attention.

## Onboard a business (15 min, with them)

Follow `stevejobless/SKILL.md` verbatim: clone kernel YAML → register project
→ PUT kernel → set autonomy → connect WhatsApp → connect voice → verify first
job end-to-end. If qualify→survey < 40%, trim the photo ask to 2 photos.

## Buy a domain (human confirms spend once)

```bash
# 1. check (checker prefilter + live prices, cheapest first)
GET /api/domains/check?domain=x.dev
# 2. prepare (fails closed on unavailable / over-budget)
POST /api/domains/prepare {"domain":"x.dev","max_price":25,"registrant_email":"…"}
# 3. approve → one-time token out
POST /api/domains/{id}/approve
# 4. register (rechecks availability + price drift first)
POST /api/domains/{id}/register {"approval_token":"…"}
# 5. wire (zone → NS → routing → worker → steve business)
POST /api/domains/{id}/wire?worker=cmail
```

Provider order in `auto`: Cloudflare (at-cost, already home) → Porkbun →
name.com. Excluded TLDs short-circuit with the reason; Porkbun covers them,
then NS-moves to Cloudflare in seconds. Sandbox/dev defaults everywhere until
`DOMAINS_ALLOW_LIVE=1`.

## After-hours call flow (what happens while you sleep)

Voice/WhatsApp/SMS/email → intake → Job + transcript + `HumanAction`. Urgent →
priority 100 (wake-now). Everything else batches to the desk with quote draft,
slots, verdict, and one-click actions. Transcripts TTL-sweep at 90 days.

## Backups + restore

Nightly 03:30 systemd timer → R2 `backups/stevejobless/`. Restore: download
object, stop `stevejobless.service`, replace `/root/stevejobless.db`, start.
Script: `stevejobless/scripts/backup.sh`. Local fallback in `/root/backups/`.

## When something breaks

1. `POST /api/tradie/{slug}/reconcile` — tells you which backend is down and why.
2. `journalctl -u stevejobless.service -n 20` / `-u steve-tunnel.service`.
3. `wrangler tail` on cmail for worker-side errors.
4. Every money path keeps a receipt: deal receipts, invoice rows, audit log.
