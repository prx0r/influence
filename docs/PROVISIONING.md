# Provisioning — the actual job: idea → name → domain → email → phone → socials

This repo is not a "create an influencer" program. The influencer object is
just where a finished provisioning chain terminates. The work is the chain:

```
idea → name candidates → check everywhere → cheapest registrar →
human buys → DNS/zone → mailbox receives → number provisions →
socials claimed → endpoint resolved
```

Every step observes first (evidence, no authority) and acquires only behind
a human gate plus a grant. Nothing below spends money on its own.

## Where each step lives

| Step | Connector / service | Observe (live?) | Acquire (how?) |
|---|---|---|---|
| name candidates | checker `POST /api/mine` + `docs/NAMING.md` | live service | human picks |
| check everywhere | `names` connector → checker `verify/handles/claim_kit` | live | n/a (read-only) |
| cheapest registrar | checker `GET /api/registrar/:domain` | live | human clicks buy link |
| buy domain | `docs/BUY-DOMAIN.md` flow (check→prepare→approve→register→wire) | — | human + approval token, `DOMAINS_ALLOW_LIVE=1` guard |
| DNS/zone | `zone` connector (DoH NS + CF zone confirm) | live | human moves NS |
| mailbox receives | `mail` connector + `docs/EMAIL.md` | structure only | human wires Email Routing |
| number provisions | `number` connector + `docs/PHONE.md` | bridge matrix | human buys (Telnyx pattern) |
| socials claimed | `social` connector | guided | human completes login/CAPTCHA |

## Source map (cmail, read-only reference — patterns only, never pasted)

- Name science + checker API: `cmail/domainnamechecker/docs/NAMING_SCIENCE.md`,
  `DOMAIN_ANIMAL_SCIENCE.md`, `socialintel.md`, `SPEC.md` (worker v3.3.0 live).
- Domain buy machine: `cmail/stevejobless/stevejobless/domains.py` +
  `domain_routes.py`, runbook in `cmail/docs/GUIDE.md` ("Buy a domain").
- Phone backend: `cmail/stevejobless/stevejobless/telephony.py` (Telnyx REST).
- Workspace + queue pattern: `cmail/docs/GUIDE.md`, `RECIPES.md` #5 (claim kit).

## Honest limits (2026-09-18)

- No registrar keys exist in any vault → no machine buying, anywhere.
  Correct: the machine compares, prepares, and drafts; the human buys.
- No Telnyx creds → numbers are bridge-selected, never provisioned.
- No mailbox provider wired → mail is desired-state + human wiring steps.
- Social logins/CAPTCHAs are human-only by policy, both repos agree.
