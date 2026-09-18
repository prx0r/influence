# HANDOVER — agentic business stack (2026-09-10)

Owner: prx0r. Backend track (this repo) + voice track (`prx0r/voiceagent`).

## Repo map

| Repo | Role | Home | State |
|---|---|---|---|
| `prx0r/cmail` (**this repo**) | hub: `cmail/` email bus, `stevejobless/` brain, `domainnamechecker/` names, `voiceagentfeedback/` notes for voice side | `/tmp/cmail-repo` staging → GitHub; live code in `/root/{cmail,stevejobless,domainnamechecker}` | pushed `1ca77f4`, more uncommitted work in trees (see §4) |
| `prx0r/voiceagent` | realtime conversation (Qwen-Omni + LiveKit) | `/root/voiceagent` + `/tmp/voiceagent-upstream` | other agent; our kernel copies sit untracked there |
| `prx0r/domainarena` | name.com buy engine (reference, ported) | `/root/agentseolab` | untouched, clean |

## Live infra (all systemd, all green)

- `cmail.tradesprior.workers.dev` — email bus, drafts queue, MCP, quarantine screen
- `steve.intelligentothers.xyz` → stevejobless :35433 — brain, desk, 88 tests
- `domainnamechecker.tradesprior.workers.dev` — verify + handles + claim_kit (v3.3.0)
- Tunnel `steve-bridge`, D1/R2/KV provisioned. Secrets: agent-vault `oracle`
  + `/etc/stevejobless.service.d/*` (root-only). Nothing secret in any repo.

## Open threads (blocked items + who unblocks)

1. **Inbound email never arrived** — rule + MX live, zone routing `unconfigured`. Needs root-MX decision on tantrafiles (flips Zoho) or a fresh domain. OWNER.
2. **$4.99 CF purchase** — needs dashboard billing/contact/agreement. NOT discussed further per owner (dropped).
3. **Outbound email** — needs Workers Paid $5/mo. Flip on migration day.
4. **WhatsApp/IG sends** — need Meta tokens. Voice/agent P0s — other agent.
5. **Porkbun/Telnyx keys** — accounts not created. Nothing code-blocked.
6. **GitHub push token** — pasted token works via askpass; rotate it (it's in chat history).
7. **Uncommitted work**: stevejobless tree (all backend work), domainnamechecker handles — next push must re-sync `/tmp/cmail-repo` first (it's a copy, not a linked checkout!).

## 10 next dev steps (ordered)

1. **SQLite→R2 nightly backup** — only data-loss risk left. systemd timer, 10 lines.
2. **Drafts UI in cmail** — approve/send buttons for migration day.
3. **Renewal alerts → desk actions** — monitor exists, not yet in the morning queue.
4. **Inbound decision** (thread 1) — flip or fresh domain, then close the last unverified hop.
5. **Social inbox→lead for IG** — webhook exists; needs tokens (thread 4).
6. **Second pilot business onboard** — run SKILL.md for real, prove multi-tenancy with live data.
7. **Calibration review** — check verdict bands once real jobs close; tune kernel weights.
8. **Voice P0 verification** — re-audit `prx0r/voiceagent` against `voiceagentfeedback/02-security.md` before any production caller.
9. **Git hygiene** — one push flow (sync script, not manual cp), rotate GitHub token.
10. **Tax lite** — VAT quarterly is built; accountant handoff format after first real invoice.
