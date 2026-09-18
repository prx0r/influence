# REPRODUCE — prove it all works

Run top to bottom. Every step has an expected receipt. No creds needed except
where marked (those degrade honestly instead).

```bash
# 1. suites (expect 80+ / 13 green)
cd stevejobless && .venv/bin/python -m pytest tests/ -q
cd ../cmail && npx tsc --noEmit && npx vitest run

# 2. brain live
curl -s https://steve.intelligentothers.xyz/ -o /dev/null -w "desk:%{http_code}\n"
curl -s -X POST https://steve.intelligentothers.xyz/api/tradie/sparky/reconcile \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['channels'])"
# expect kernel READY, honest MISSINGs elsewhere

# 3. intake → quote → slots → confirm → invoice (expect ids + £ maths)
S=https://steve.intelligentothers.xyz
R=$(curl -s -X POST $S/api/tradie/sparky/intake -H 'content-type: application/json' \
  -d '{"customer_name":"R","customer_phone":"+447000000001","job_type":"fault","description":"t"}')
echo $R | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['job_id'], [o['id'] for o in d['options']])"

# 4. bus + checker live
curl -s https://cmail.tradesprior.workers.dev/api/stats
curl -s https://domainnamechecker.tradesprior.workers.dev/api/handles/octocat \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['summary'])"

# 5. injection screen (expect quarantine, queue untouched)
# POST /test/ingest with override text → search shows classification=quarantine, needs_reply=0

# 6. claim → prepare (no spend; needs name.com/Porkbun creds or returns the 409 next step)
curl -s -X POST $S/api/domains/claim -H 'content-type: application/json' \
  -d '{"domain":"zzsweep99999.dev","max_price":25,"registrant_email":"you@x.com"}'
```

Live deployment receipts (2026-09-10): name.com dev REGISTERED deal 2;
attack ingest quarantined live; $4.99 CF prepare; renewals/sweep/feed verified.
See `HANDOVER.md` for infra + open threads.
