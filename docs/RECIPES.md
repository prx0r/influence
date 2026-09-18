# RECIPES — copy-paste runs

Each recipe: intent → commands → expected receipt. Replace slugs/ids.

## 1. Register business + load kernel

```bash
curl -X PUT localhost:8787/api/tradie/sparky/kernel \
  -H 'content-type: application/json' -d @kernel.json
curl localhost:8787/api/tradie/sparky/kernel | python3 -c "import json,sys; print(list(json.load(sys.stdin)['kernel']))"
# expect: ['preferences', 'after_hours_multiplier', ..., 'price_book']
```

## 2. Log an after-hours call (voice-agent shape)

```bash
curl -X POST localhost:8787/api/tradie/sparky/intake -H 'content-type: application/json' -d '{
  "customer_name":"A","customer_phone":"+447000000001","job_type":"ev_charger",
  "description":"wallbox","transcript":"…","urgent":false,"after_hours":true,"distance_km":8}'
# expect: {"ok":true,"job_id":N,"action_id":M,"autonomy":"semi_auto","options":[…]}
```

## 3. Quote → confirm → schedule → invoice

```bash
J=1
curl -X POST localhost:8787/api/tradie/sparky/jobs/$J/quote
curl localhost:8787/api/tradie/sparky/slots | head -c 200
curl -X POST localhost:8787/api/tradie/sparky/jobs/$J/confirm \
  -H 'content-type: application/json' -d '{"scheduled_at":"2026-09-12T09:00:00+00:00"}'
curl -X PATCH localhost:8787/api/tradie/sparky/jobs/$J \
  -H 'content-type: application/json' -d '{"status":"done","final_price":420,"duration_min":200}'
curl -X POST localhost:8787/api/tradie/sparky/jobs/$J/invoice
curl localhost:8787/api/tradie/sparky/tax/quarter
# expect: invoice SPARKY-0001, vat 84.00, quarter totals
```

## 4. Big-quote call-back gate (≥£500 default)

```bash
curl -X POST localhost:8787/api/tradie/sparky/jobs/$J/quote/$Q/send  # → 409
curl -X POST localhost:8787/api/tradie/sparky/jobs/$J/callback \
  -H 'content-type: application/json' -d '{"verifier":"tradie:voice:+447…"}'
curl -X POST localhost:8787/api/tradie/sparky/jobs/$J/quote/$Q/send  # → approved/sent
```

## 5. Check a name everywhere + claim kit

```bash
curl domainnamechecker.tradesprior.workers.dev/api/handles/myname
curl -X POST domainnamechecker.tradesprior.workers.dev/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"claim_kit","arguments":{"domain":"myname.dev"}}}'
```

## 6. Sweep old transcripts (GDPR)

```bash
curl -X POST localhost:8787/api/tradie/sparky/sweep          # → 400, needs confirm
curl -X POST "localhost:8787/api/tradie/sparky/sweep?confirm=true"
# expect: {"deleted":N,"jobs_touched":M} — job metadata kept
```

## 7. Backup now + verify in R2

```bash
systemctl start steve-backup.service
journalctl -u steve-backup.service -n 3 | grep uploaded
```

## 8. Full test suites

```bash
cd stevejobless && .venv/bin/python -m pytest tests/ -q   # 80+
cd ../cmail && npx tsc --noEmit && npx vitest run          # 13
```
