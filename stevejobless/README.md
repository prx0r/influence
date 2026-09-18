# SteveJobless

**Studio operations for one-person app factories.**

SteveJobless keeps one canonical "studio passport" for every product, reconciles desired state against reality, automatically completes safe work when allowed, and turns everything else into one-at-a-time human actions.

## What the MVP does

- Project passports for Drawdle, Feedify, Breadup (seeded demo projects)
- Reconciliation engine with resource states: `READY`, `MISSING`, `BLOCKED`, `UNKNOWN`, `ERROR`
- Human action queue: the only things the founder should have to think about
- GitHub inspection using the GitHub REST API when `GITHUB_TOKEN` is present
- Domain/DNS + production URL checks
- App Store Connect adapter using `asc-cli` when installed/configured
- Social-account state tracking without brittle scraping
- Safe-mode mutation gate: external writes are disabled unless explicitly opted in
- Autopilot observe → act → verify loop for locally safe generated artifacts
- Mobile-first PWA-style dashboard
- Minimal SwiftUI iOS client source using the same API
- Audit trail for every reconciliation run

## Architecture

```text
               SteveJobless UI / iOS
                       |
                    REST API
                       |
                 Studio State Graph
                       |
                 Reconciler / Agent
          _____________|________________
         |        |          |           |
       GitHub    DNS       App Store    Social
       REST      HTTP       asc-cli      state
                              |
                          browser fallback
                         (Stagehand later)
```

The key abstraction is **desired state vs observed state**. Steve does not ask you to remember setup tasks; it asks connectors what is true and emits the smallest possible queue of actions.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
steve init
steve serve
```

Then open <http://127.0.0.1:8787>.

Or:

```bash
docker compose up --build
```

## Useful commands

```bash
steve init                         # create DB + seed demo projects
steve projects                     # list projects
steve reconcile                    # reconcile every project
steve reconcile drawdle            # reconcile one project
steve autopilot drawdle            # execute safe AUTO work then verify
steve serve                        # web/API server
```

## Real integrations

### GitHub

Set:

```bash
export GITHUB_TOKEN=github_pat_...
```

A passport resource like `prx0r/drawdle` will be inspected via the public GitHub API.

### App Store Connect

Steve uses [`tddworks/asc-cli`](https://github.com/tddworks/asc-cli) as its Apple adapter rather than reimplementing Apple's API surface.

```bash
brew install asccli
asc auth login --key-id ... --issuer-id ... --private-key-path ...
export STEVE_ASC_ENABLED=1
```

Steve calls `asc apps list` and consumes structured JSON. Mutating App Store commands are intentionally not enabled in the MVP.

### Browser automation

`vendor/bootstrap_upstreams.sh` pins/clones Stagehand for sites that have no robust API. This MVP exposes the boundary but intentionally does not automate CAPTCHAs, 2FA, legal acceptance, banking, or tax flows. Those become `HUMAN` actions.

## Passport format

See `examples/passport.drawdle.json`. A passport describes what the company *should* look like. It does not contain secrets.

## Safety model

- `STEVE_SAFE_MODE=1` by default.
- Read/inspect operations are allowed.
- External writes are denied unless a connector is explicitly enabled.
- 2FA, CAPTCHAs, legal agreements, banking/tax forms remain human actions.
- Secrets stay in environment variables or external secret stores; never in passports.

## Upstream projects

See `vendor/UPSTREAMS.md`. The bootstrap script clones pinned upstreams into `vendor/upstreams/` for local development, but they are **not vendored into this repository or archive**. This avoids dragging huge codebases and incompatible licenses into Steve.

## Next build targets

1. OAuth connector registry (GitHub, Cloudflare, X, Meta, TikTok, YouTube)
2. Stagehand worker service for browser-only account setup
3. App Store screenshot + localization automation via `asc-cli`
4. Cloudflare DNS/site deployment adapter
5. Background reconcile scheduler + push notifications
6. Credential broker (Infisical / 1Password / system keychain)
7. Native iOS approval remote with APNs
