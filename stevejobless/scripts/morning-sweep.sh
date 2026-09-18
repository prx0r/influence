#!/bin/bash
# Morning sweep: reconcile every tradie business + sync renewal alerts.
# Desk is warm before anyone wakes. Logs to journal.
set -u
BASE="${STEVE_URL:-http://127.0.0.1:35433}"
for slug in sparky flowright; do
  curl -s -m 60 -X POST "$BASE/api/tradie/$slug/reconcile" -o /dev/null -w "reconcile $slug: %{http_code}\n"
done
curl -s -m 60 -X POST "$BASE/api/domains/renewals/sync" -o /dev/null -w "renewals sync: %{http_code}\n"
