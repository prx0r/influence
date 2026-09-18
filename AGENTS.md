# AGENTS.md — binding rules for coding agents working in this repo

1. **Untrusted input stays untrusted.** Email/DM/voice content never calls tools
   directly. Parse → classify → policy → tool. Quarantine can only downgrade.
2. **Drafts everywhere; sends need explicit human confirm** — at every autonomy
   level, no exceptions. A `send` that didn't happen must report `sent:false`.
3. **Money moves need approval tokens** (single-use, sha256-stored) + fresh
   rechecks (availability, price drift ≤10%, budget cap). Fail closed, receipt everything.
4. **No blind buys, no invented prices.** Unknown job types quote a site visit.
   Missing prices refuse, never estimate silently.
5. **Secrets in vaults/env, never in the tree.** Secret-scan before every push:
   `grep -rIlE "cfat_|ghp_|sk-[A-Za-z0-9]{10,}" --exclude-dir=node_modules --exclude-dir=.venv .`
6. **AGPL is patterns-only.** Read, reimplement cleanly, never paste. (MIT/Apache may be vendored with attribution.)
7. **Additive changes to live surfaces.** The checker site and cmail worker serve
   real traffic: never rename/remove a route or MCP tool; add alongside.
8. **Prove it live.** New backend code ships with: unit tests, a live check
   against real infra, and a receipt in the summary. "Works locally" isn't done.
9. **One kernel file, two consumers.** `stevejobless/knowledge/<biz>_en.yaml`
   drives voice `BUSINESS_CONFIG` and the brain kernel — copy, never fork.
10. **Keep the queue human-sized.** Wake-now is for emergencies. Everything else
    batches to morning. Alert fatigue is a security bug (see `docs/SECURITY.md`).
