# Upstream integration manifest

SteveJobless does **not** copy these projects into its source tree. Use `bootstrap_upstreams.sh` to clone them for local development/reference.

| Project | Role | Repository | License note |
|---|---|---|---|
| asc-cli | App Store Connect machine interface | `tddworks/asc-cli` | verify upstream LICENSE before redistribution; MVP invokes the installed binary |
| Blitz | Apple release UX/MCP patterns | `blitzdotdev/blitz-mac` | inspect upstream license before reusing code |
| Stagehand | browser fallback / deterministic AI browser flows | `browserbase/stagehand` | MIT at time of research; verify pinned revision |
| Activepieces | integration/workflow reference | `activepieces/activepieces` | large project; use as integration/reference, not vendored code |
| Postiz | social scheduling reference/service | `gitroomhq/postiz-app` | AGPL-3.0; keep across an API/process boundary if used commercially |

The script records commit SHAs after cloning. Pin those SHAs before production use.
