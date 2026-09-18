# Social Media Tools Research for SteveJobless

Research conducted on open-source social media management tools, MCP servers, content creation tools, analytics tools, and credential management solutions.

---

## 1. Open-Source Social Media Managers

### Postiz (gitroomhq/postiz-app)
- **GitHub:** https://github.com/gitroomhq/postiz-app
- **What it does:** Ultimate agentic social media scheduling tool. Alternative to Buffer, Hypefury, Twitter Hunter. Schedule posts, measure analytics, collaborate with team members.
- **Stars/Forks:** 15K+ / 2K+ (as of search results)
- **License:** AGPL-3.0
- **SteveJobless Integration:** Perfect for campaign scheduling. API available for automation with N8N, Make.com, Zapier. Supports multiple social platforms.
- **MCP Server:** Yes - has MCP server for AI agent integration

### BrightBean Studio (brightbeanxyz/brightbean-studio)
- **GitHub:** https://github.com/brightbeanxyz/brightbean-studio
- **What it does:** Open-source, self-hostable social media management platform. Schedule, publish, and manage content across 10+ platforms. Free alternative to Buffer, Sendible, SocialPilot.
- **Stars/Forks:** 1,845 / 369
- **License:** AGPL-3.0
- **SteveJobless Integration:** One-click deploy on Heroku, Render, Railway. Supports 10+ platforms including Facebook, Instagram, LinkedIn, TikTok, YouTube, Pinterest, Threads, Bluesky, Google Business Profile, Mastodon.
- **MCP Server:** Yes - MCP tools documented

### TryPost (trypostit/trypost)
- **GitHub:** https://github.com/trypostit/trypost
- **What it does:** Open-source social media scheduling with AI copilot, native publishing to 12 networks, and MCP server for AI assistants to post.
- **Stars/Forks:** 423 / 97
- **License:** AGPL-3.0
- **SteveJobless Integration:** MCP server allows Claude, Cursor, ChatGPT to draft, schedule, and publish posts. Supports 12 platforms.
- **MCP Server:** Yes - first-class MCP server and REST API

### Shoutrrr (coollabsio/shoutrrr)
- **GitHub:** https://github.com/coollabsio/shoutrrr
- **What it does:** Open-source alternative to Buffer, Typefully, and Hootsuite. Write once and schedule everywhere. Supports X, Bluesky, LinkedIn, Facebook, Instagram, Threads, and Discord.
- **Stars/Forks:** 305 / 36
- **License:** Apache License 2.0
- **SteveJobless Integration:** Laravel 13 + React 19 app. OAuth token management built-in. Supports queue and calendar management.
- **MCP Server:** No (but has API)

### PendPost (pendpost/pendpost)
- **GitHub:** https://github.com/pendpost/pendpost
- **What it does:** Agent-first social media planner with human approval gate. AI agent drafts and schedules posts across 12+ platforms. MCP-native with 120 tools.
- **Stars/Forks:** 6 / 2
- **License:** MIT License
- **SteveJobless Integration:** Zero-dependency Node process with REST API at `/api` and MCP server at `/mcp`. Supports Instagram, Facebook, LinkedIn, YouTube, X, Telegram, Discord, Mastodon, Nostr, WordPress, Ghost.
- **MCP Server:** Yes - 120 tools available

### Hookpost (jatinder14/hookpost)
- **GitHub:** https://github.com/jatinder14/hookpost
- **What it does:** All-in-one open-source social media scheduler and multi-agent AI copilot. Postiz/Buffer alternative. Publish to 30+ social networks.
- **Stars/Forks:** 0 / 0
- **License:** AGPL-3.0
- **SteveJobless Integration:** CLI and MCP server. Supports Claude, ChatGPT, OpenClaw, Hermes. Native REST API, Webhooks, and integrations with N8N and Make.com.
- **MCP Server:** Yes - CLI (`npx hookpost`) and MCP server

### SocialFlow (inbharatai/SocialFlow)
- **GitHub:** https://github.com/inbharatai/socialflow
- **What it does:** Open-source AI social media workflow engine for planning, drafting, brand voice, image generation, and platform-aware content automation.
- **Stars/Forks:** 30 / 7
- **License:** MIT License
- **SteveJobless Integration:** 6 agents (Scout, Planner, Creator, Reviewer, Publisher, Analyst). Supports 12 platforms. Brand kit with colors, logo, fonts, tone.
- **MCP Server:** No (but has API endpoints)

### Socioboard (socioboard/socioboard)
- **GitHub:** https://github.com/socioboard/socioboard
- **What it does:** AI agents powered social media automation platform. Schedule posts, multi-platform deployments via CSV, manage digital assets, analyze audience impact.
- **Stars/Forks:** 1 / 2
- **License:** AGPL-3.0
- **SteveJobless Integration:** Supports Facebook, Twitter, LinkedIn, Pinterest, Snapchat Business. Dynamic analytics dashboard with AI strategic insights.
- **MCP Server:** No

### Posthive (AstaBlackClove/posthive)
- **GitHub:** https://github.com/AstaBlackClove/posthive
- **What it does:** Agentic social media scheduler to post on multi platforms with built-in MCP. Write once, publish to 14+ platforms simultaneously.
- **Stars/Forks:** 12 / 3
- **License:** AGPL-3.0
- **SteveJobless Integration:** 10 MCP tools: `list_accounts`, `create_post`, `get_post`, `list_scheduled_posts`, `approve_draft`, `update_post`, `duplicate_post`, `delete_post`, `list_templates`, `create_from_template`
- **MCP Server:** Yes - 10 tools

### OpenPost (rodrgds/openpost)
- **GitHub:** https://github.com/rodrgds/openpost
- **What it does:** Create, adapt, schedule, and publish content across platforms. Single-binary Go app with Svelte frontend.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Calendar and scheduling, analytics, content adaptation. API, CLI, and MCP server available.
- **MCP Server:** Yes

### Mixpost (inovector/mixpost)
- **GitHub:** https://github.com/inovector/mixpost
- **What it does:** Schedule, publish, and manage social media content on your server. Buffer alternative. Laravel-based.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Queue and calendar management. Team collaboration features.
- **MCP Server:** No (but has API)

### Open-Dispatch (Matthew-Selvam/Open-Dispatch)
- **GitHub:** https://github.com/Matthew-Selvam/Open-Dispatch
- **What it does:** One API to dispatch content to 7 social platforms. Self-host free, MIT licensed. The open-source alternative to Buffer/Hootsuite.
- **Stars/Forks:** 3 / 1
- **License:** MIT License
- **SteveJobless Integration:** JSONL queue, exponential retry, webhooks. Supports n8n, Homebrew, Docker. Has MCP server with 7 tools.
- **MCP Server:** Yes - `mcp_server.py` with 7 tools

---

## 2. Social Media MCP Servers

### 1Social MCP (sultanlive/1social-mcp)
- **GitHub:** https://github.com/sultanlive/1social-mcp
- **What it does:** Model Context Protocol server for publishing, scheduling and verifying social posts across seven networks. OAuth-secured.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Remote server at `https://mcp.1social.dev/mcp`. Streamable HTTP transport. OAuth 2.1 with PKCE.
- **MCP Server:** Yes - remote hosted

### Social Media MCP (tayler-id/social-media-mcp)
- **GitHub:** https://github.com/tayler-id/social-media-mcp
- **What it does:** MCP server connecting to multiple social media platforms. Natural language interface, research capabilities, content generation.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Supports Twitter/X, Mastodon, LinkedIn. Rate limit management, analytics tracking.
- **MCP Server:** Yes

### Social MCP (oluwaeinstein007/social-mcp)
- **GitHub:** https://github.com/oluwaeinstein007/social-mcp
- **What it does:** MCP server for interacting with social media platforms including Telegram, Twitter, Discord, WhatsApp, Facebook, Instagram, Slack, LinkedIn, Reddit, Threads, Bluesky, Mastodon, YouTube, Pinterest, Medium, Email, Dev.to, Hashnode, beehiiv, Telegram, Tumblr.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Comprehensive platform coverage. Send messages, manage posts, get analytics.
- **MCP Server:** Yes

### Instagram/Facebook MCP (bmachek/social-mcp)
- **GitHub:** https://github.com/bmachek/social-mcp
- **What it does:** MCP server for Instagram and Facebook. Post photos, carousels, Reels, schedule posts, pull engagement analytics.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Self-hosted. 25+ tools for Instagram and Facebook. Docker support.
- **MCP Server:** Yes

### Social API MCP (socialapishub/mcp-server)
- **GitHub:** https://github.com/socialapishub/mcp-server
- **What it does:** Unified social media API for AI agents. 47 tools across Facebook and Instagram.
- **Stars/Forks:** Not visible
- **License:** MIT License
- **SteveJobless Integration:** Published on npm as `@socialapis/mcp`. Python, JavaScript/TypeScript, and Go SDKs available.
- **MCP Server:** Yes - 47 tools

---

## 3. Twitter/X MCP Servers

### Twitter MCP (achetronic/twitter-mcp)
- **GitHub:** https://github.com/achetronic/twitter-mcp
- **What it does:** MCP server for Twitter/X - read, write, analyze and schedule tweets with AI assistants. Built in Go.
- **Stars/Forks:** 3 / 2
- **License:** Apache License 2.0
- **SteveJobless Integration:** 22+ tools including scheduling, trending topics, heat scores, bookmarks management.
- **MCP Server:** Yes

### X/Twitter MCP (tharuxpert/x-mcp)
- **GitHub:** https://github.com/tharuxpert/x-mcp
- **What it does:** MCP server for the X (Twitter) API - post tweets, search, read timelines, like, retweet, upload media.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Works with Claude Code, Claude Desktop, OpenAI Codex, Cursor, Windsurf, Cline. Streamable HTTP transport.
- **MCP Server:** Yes

### Twitter MCP Server (EnesCinr/twitter-mcp)
- **GitHub:** https://github.com/EnesCinr/twitter-mcp
- **What it does:** MCP server allows clients to interact with Twitter, enabling posting tweets and searching Twitter.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Simple setup with API key, API secret key, access token, access token secret.
- **MCP Server:** Yes

### X MCP Server (DataWhisker/x-mcp-server)
- **GitHub:** https://github.com/DataWhisker/x-mcp-server
- **What it does:** MCP server for X (Twitter) integration. 26 tools for reading timelines, posting, searching, engagement, user lookup, follower export.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** 26 tools available for comprehensive Twitter management.
- **MCP Server:** Yes

---

## 4. Content Creation Tools

### GEN MCP Server (poweredbyGEN/gen-mcp-server)
- **GitHub:** https://github.com/poweredbyGEN/gen-mcp-server
- **What it does:** MCP server for GEN Auto Content Engine - programmatic access to sheets, rows, cells, video layers, and content generation.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Hosted server at `https://mcp.gen.pro`. Full 5-step journey from agent onboarding to video publishing.
- **MCP Server:** Yes - hosted

### Gemini MCP (aisynclabs/Gemini-mcp)
- **GitHub:** https://github.com/aisynclabs/Gemini-mcp
- **What it does:** MCP server for Google's Gemini API focused on UI generation and frontend development.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** 8 specialized tools including `gemini_generate_ui`, `gemini_multimodal_query`, `gemini_fix_ui_from_screenshot`, `gemini_create_animation`.
- **MCP Server:** Yes

---

## 5. Analytics Tools

### Influence Hub (reforia/influence-hub)
- **GitHub:** https://github.com/reforia/influence-hub
- **What it does:** Open-source social media analytics and insights aggregator with AI integration. Connects to Facebook, YouTube, Twitter, Reddit, TikTok, Instagram, Discord.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** MCP Server for AI integration. Real-time insights and trend analysis. Secure token management.
- **MCP Server:** Yes

### Social Ops (kriptoburak/Social-ops)
- **GitHub:** https://github.com/kriptoburak/Social-ops
- **What it does:** Open-source MCP + SaaS console for social-media topic-aggregation reports across Reddit, Instagram, Facebook, X, App Store, Google Play.
- **Stars/Forks:** 0 / 0
- **License:** Not visible
- **SteveJobless Integration:** 16 MCP tools for analysis. No LLM required - deterministic NLP pipeline.
- **MCP Server:** Yes - 16 tools

### Twiligent (onions-hyy/social-media-dashboard)
- **GitHub:** https://github.com/onions-hyy/social-media-dashboard
- **What it does:** YouTube and Instagram analytics dashboard. Self-hosted, no subscription required.
- **Stars/Forks:** 0 / 0
- **License:** MIT License
- **SteveJobless Integration:** Multi-account support, scheduled publishing via GitHub Actions, token auto-refresh, zero database.
- **MCP Server:** No (but has API)

### Multiverse Insights (Prathameshsci369/Multiverse-Insights)
- **GitHub:** https://github.com/Prathameshsci369/Multiverse-Insights
- **What it does:** Real-time multimodal social media analytics platform with AI-powered analysis. Reddit, Twitter, YouTube support.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** RAG chatbot, vector database, natural language queries, dynamic dashboards, sentiment heatmaps.
- **MCP Server:** No (but has API)

### OKN Analytics (CyberSystema/okn-analytics)
- **GitHub:** https://github.com/CyberSystema/okn-analytics
- **What it does:** Python pipeline that processes weekly CSV exports from Instagram and TikTok, runs 14 ML models, generates HTML intelligence report.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Fully automated: push CSVs → GitHub Actions → report deployed to Cloudflare Pages. Trilingual NLP.
- **MCP Server:** No

---

## 6. Credential Management

### AgentCordon (agentcordon/agentcordon)
- **GitHub:** https://github.com/agentcordon/agentcordon
- **What it does:** Self-hostable Agentic Identity Provider and credential broker for AI agents. AES-256-GCM encrypted vault, Cedar policy engine, credential proxy, MCP gateway.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Three-tier architecture: CLI → Broker → Server. Credentials never leave broker boundary. Full audit trail.
- **MCP Server:** Yes - MCP gateway

### Git Org Group Cred Vault (wildfirebill-ai/git-org-group-cred-vault)
- **GitHub:** https://github.com/wildfirebill-ai/git-org-group-cred-vault
- **What it does:** MCP server that stores GitHub and GitLab tokens in an encrypted vault and retrieves them by org/group keyword.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Automatic credential resolution. Per-project scoping. Self-hosted on Windows, Linux, macOS, Docker/Unraid.
- **MCP Server:** Yes

### GAM - GitHub Account Manager (miguelbalvin-dev/GAM)
- **GitHub:** https://github.com/miguelbalvin-dev/gam
- **What it does:** Manage multiple GitHub accounts from terminal. OAuth Device Flow, secure token storage in OS keychain.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Tokens stored in OS keychain (macOS Keychain, Windows Credential Manager, Linux SecretService). Git credential helper integration.
- **MCP Server:** No

### GitHub Token Manager (isometry/github-token-manager)
- **GitHub:** https://github.com/isometry/github-token-manager
- **What it does:** Kubernetes operator to manage fine-grained, ephemeral Access Tokens generated from GitHub App credentials.
- **Stars/Forks:** Not visible
- **License:** Not visible
- **SteveJobless Integration:** Zero-Trust Security, ephemeral & auto-rotating tokens, fine-grained permissions, multi-tenancy, GitOps-ready.
- **MCP Server:** No

---

## 7. Best Practices for Social API Token Storage

Based on research from GitHub documentation and security best practices:

1. **Never hardcode credentials** in code or repositories
2. **Use OS-native secret storage**:
   - macOS: Keychain
   - Windows: Credential Manager
   - Linux: libsecret/SecretService
3. **Implement OAuth 2.0 with PKCE** for secure token exchange
4. **Use short-lived tokens** with automatic refresh
5. **Encrypt tokens at rest** using AES-256-GCM
6. **Implement audit logging** for all credential access
7. **Use environment variables** or secret managers (Azure Key Vault, HashiCorp Vault)
8. **Rotate credentials regularly** and have a breach response plan
9. **Implement least-privilege access** - only request necessary scopes
10. **Use GitHub Apps** instead of Personal Access Tokens where possible

---

## 8. Recommended Integration Strategy for SteveJobless

### Phase 1: Core Scheduling
- **Primary Tool:** Postiz or BrightBean Studio (both have MCP servers)
- **Alternative:** TryPost or Hookpost for more MCP-native approach
- **Benefits:** Multi-platform scheduling, AI copilot, team collaboration

### Phase 2: Analytics & Insights
- **Primary Tool:** Influence Hub (has MCP server)
- **Secondary:** Social Ops for topic aggregation reports
- **Benefits:** Real-time analytics, trend detection, audience insights

### Phase 3: Content Generation
- **Primary Tool:** GEN MCP Server or Gemini MCP
- **Benefits:** AI-powered content creation, video generation

### Phase 4: Credential Management
- **Primary Tool:** AgentCordon (has MCP gateway)
- **Alternative:** Git Org Group Cred Vault for simpler use cases
- **Benefits:** Encrypted vault, policy engine, audit trail

### MCP Server Integration Points
1. **Postiz/TryPost** → Schedule and publish posts
2. **Influence Hub** → Fetch analytics and insights
3. **Twitter MCP** → Twitter-specific operations
4. **AgentCordon** → Secure credential management
5. **Social Ops** → Topic aggregation and reporting

---

## 9. Quick Reference Table

| Tool | Category | MCP Server | License | Stars | Best For |
|------|----------|------------|---------|-------|----------|
| Postiz | Scheduler | Yes | AGPL-3.0 | 15K+ | Full-featured scheduling |
| BrightBean Studio | Scheduler | Yes | AGPL-3.0 | 1,845 | Multi-platform management |
| TryPost | Scheduler | Yes | AGPL-3.0 | 423 | AI copilot integration |
| PendPost | Scheduler | Yes | MIT | 6 | Agent-first workflow |
| Hookpost | Scheduler | Yes | AGPL-3.0 | 0 | 30+ networks |
| SocialFlow | Workflow | No | MIT | 30 | AI content pipeline |
| Open-Dispatch | Dispatcher | Yes | MIT | 3 | API-first approach |
| 1Social MCP | MCP Server | Yes | N/A | N/A | OAuth-secured posting |
| Social MCP | MCP Server | Yes | N/A | N/A | Multi-platform coverage |
| Twitter MCP | MCP Server | Yes | Apache-2.0 | 3 | Twitter specialization |
| Influence Hub | Analytics | Yes | N/A | N/A | AI-powered insights |
| Social Ops | Analytics | Yes | N/A | 0 | Topic aggregation |
| AgentCordon | Credentials | Yes | N/A | N/A | Enterprise security |

---

*Research conducted on 2026-09-08*
