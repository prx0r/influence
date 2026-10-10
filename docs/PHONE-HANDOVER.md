# Phone handover — OddHobb brand phone

> Last verified: 2026-10-05. Status: **edge live, real-traffic untested.**
> Number: `+44 7822 000802` (Telnyx GB mobile, active). Public edge: `https://phone.agentcom.org`.

---

## What works (verified from the box)

| Check | Result |
|-------|--------|
| `phone.agentcom.org/` landing | 200 |
| `/app` phone UI (SMS/calls/callbacks/dialer) | 200, JS parses clean |
| `/v1/status`, `/v1/health` | 200 |
| Worker fallback `oddhobb-phone.tradesprior.workers.dev` | 200 |
| Local proxy `:8794` | 200 |
| Tunnel `phone-agentcom` | healthy, 4 conns |
| SMS webhook → inbox read | proven E2E (test events) |
| Call hangup → callback queue | proven E2E (test events) |
| Dash MCP `phone.*` | reads inbox |
| SIP credential `oddhobb-browser` | active, bound to QuickCall SIP |
| OVP whitelist | US + CA + **GB** |
| `/v1/voice/creds` (Bearer) | returns SIP login |

## What changed without us (2026-10-05)

Messaging profile `4001a0d8-…` is now **attached to the number** (was null).
Inbound SMS should now deliver to Telnyx → webhook → inbox. **Not yet proven with a real message.**

## NOT proven (do these next)

1. **Real inbound SMS** — text the number from a personal mobile, check `/app` SMS tab
2. **Real inbound call** — call the number, check call log + callback queue
3. **Browser dialer registration** — open `/app` → Voice → Register (needs mic permission)
4. **Browser outbound call** — 10-second test call, then hang up (metered ~$0.007/min)
5. **Inbound ringing in browser** — register, then call the number from another phone

## Known gaps / suspects

| # | Symptom area | Notes |
|---|--------------|-------|
| 1 | Real SMS never arrives | Profile was unattached until recently; retest now. If still dead: check Telnyx Mission Control → number → Messaging, and message logs in portal |
| 2 | Real calls don't ring browser | Number routes to QuickCall SIP credential connection; browser must be **registered at that moment**. No registration = no ring. No voicemail/failover configured |
| 3 | Dialer Register fails | Browser needs mic permission + WSS to Telnyx reachable. Check `/v1/voice/creds` returns login (it does). Try Chrome/Firefox, allow mic |
| 4 | Outbound UK fails | OVP now includes GB. If blocked: check Telnyx balance / outbound profile on connection |
| 5 | `phone.agentcom.org` flaky from outside | Tunnel runner died twice before; single runner now + remote ingress config. If 404/1033 returns: check `phone_tunnel` process + `phone_proxy.py` on `:8794` |
| 6 | `/messages`, `/calls` list endpoints 404 | Normal — those paths don't exist on Telnyx v2 API. Use webhooks + portal message logs instead |

## Architecture (don't get mixed up)

```
Telnyx number +447822000802 (active, MP attached)
  ├── voice → connection QuickCall SIP (credential_connection)
  │     └── browser registers via oddhobb-browser SIP creds (WebRTC)
  ├── SMS → messaging profile QuickCall → webhook → phone.agentcom.org/v1/telnyx/sms
  ├── calls → Call Control app QuickCall Browser → webhook → …/v1/telnyx/call
  └── edge: phone.agentcom.org (tunnel) → 127.0.0.1:8794 (proxy) → worker + KV inbox
influence dash (agentcom.org) reads the inbox via phone.* tools
```

## Secrets (vault `oracle`, never in chat/files)

`TELNYX_API_KEY` · `TELNYX_SIP_USER` · `TELNYX_SIP_PASSWORD` · `ODDHOBB_PHONE_AUTH` ·
`ODDHOBB_PHONE_WORKER_URL` · `PHONE_WEBHOOK_BASE` · `TELNYX_CALL_CONTROL_APP_ID` ·
`CLOUDFLARE_API_TOKEN_NEW` · `R2_S3_ACCESS_KEY_NEW` · `R2_S3_SECRET_KEY_NEW`

⚠️ CF token + R2 keys were pasted in chat on 2026-10-05 — **rotate them**, then swap vault values.

## Processes that must stay up

| Process | What | Restart |
|---------|------|---------|
| `phone_proxy.py` (`:8794`) | local edge proxy | `python3 /root/influence/dash/phone_proxy.py` (nohup) |
| `cloudflared … phone token` | tunnel (single runner only!) | token in `dash/phone_tunnel_token` (0600) |
| `dash/server.py` (`:8793`) | influence dash | `serve-perm.sh` |

Never run two phone-tunnel runners — stale ones serve 404s.

## Spend rules (unchanged)

Inbound SMS free · inbound voice ~$0.0032/min · UK outbound from ~$0.007/min.
Nothing spends until a real call connects or an approved SMS sends.
No number purchases without explicit owner confirm.

## Related

- `oddhobbies/docs/commerce/BRAND-PHONE.md` — full runbook
- `oddhobbies/docs/commerce/TELNYX-CAPABILITIES.md` — Telnyx map
- `oddhobbies/stores/oddhobb/SOCIAL-CLAIM-RUNBOOK.md`
- Worker source: `/tmp/opencode/phone-worker/` (**not in git — move into influence before it rots**)
