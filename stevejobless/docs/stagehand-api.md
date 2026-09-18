# Stagehand — AI Browser Automation Framework

**GitHub:** https://github.com/browserbase/stagehand
**Docs:** https://docs.stagehand.dev
**License:** MIT

Stagehand is an AI-powered browser automation framework that lets you control browsers using natural language.

## Quick Start

### TypeScript
```typescript
import { localBrowser, Stagehand } from "@browserbasehq/stagehand";

const browser = await localBrowser.launch();
const stagehand = await Stagehand.create({ browser });
const page = await browser.context.activePage();
await page.goto("https://example.com");
await stagehand.close();
await browser.close();
```

### Python
```python
from stagehand import Stagehand, local_browser

browser = await local_browser.launch()
stagehand = await Stagehand.create(browser=browser)
page = await browser.context.active_page()
await page.goto("https://example.com")
await stagehand.close()
await browser.close()
```

## Core API

### `Stagehand.create()`
Create a Stagehand instance connected to a browser.

**Parameters:**
- `browser` (required): A browser handle from `browserbase.launch()`, `localBrowser.launch()`, etc.
- `apiKey` (optional): Browserbase API key
- `apiUrl` (optional): Stagehand API origin override
- `model` (optional): Default model configuration
- `systemPrompt` (optional): Additional system instructions
- `selfHeal` (optional): Re-infer and retry cached actions when selector changes
- `domSettleTimeoutMs` (optional): Max wait for DOM to settle
- `cache` (optional): Server-side cache setting
- `logging` (optional): Client-side log level and output format

### `act(instruction)`
Perform an action described in natural language.
```typescript
await stagehand.act("Click the sign in button");
```

**Options:**
- `cache`: Override server-side caching
- `locator`: Page locator identifying the action target
- `model`: Model configuration for this call
- `timeout`: Operation timeout in ms
- `variables`: Variables available to the instruction

### `observe(instruction)`
Find candidate actions on the page.
```typescript
const actions = await stagehand.observe("Find the sign in button");
```

### `extract(instruction, schema)`
Extract structured data from the page.
```typescript
const product = await stagehand.extract("Extract the product", ProductSchema);
```

### `close()`
Close the Stagehand runtime and release resources.

### `metrics()`
Return token usage and inference timing metrics for the session.

## Configuration

### Browserbase Options
- `apiKey`: Browserbase API key (required for BROWSERBASE env)
- `browserbaseSessionId`: Resume existing session

### Local Browser Options
- `localBrowserLaunchOptions`: Browser launch configuration

### LLM Configuration
- `model`: Provider-prefixed model name (e.g., `anthropic/claude-sonnet-4-6`)
- `llmClient`: Custom LLM client instance

### Environment Variables
| Variable | Description |
|----------|-------------|
| `BROWSERBASE_API_KEY` | Browserbase API key |
| `API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |

## Python Specifics

```python
stagehand = await Stagehand.create(
    browser=browser,
    model="anthropic/claude-sonnet-4-6",
    model_api_key="your-api-key",
    self_heal=True,
    dom_settle_timeout_ms=3000,
)
```

## Server API v4

Stagehand exposes a v4 OpenAPI server:
- `POST /browsersession` — Create browser session
- `POST /browsersession/{id}/act` — Perform action
- `POST /browsersession/{id}/observe` — Observe page
- `POST /browsersession/{id}/extract` — Extract data
- `POST /browsersession/{id}/navigate` — Navigate to URL

**Security:**
- `BrowserbaseApiKey`: `x-bb-api-key` header
- `BrowserbaseProjectId`: `x-bb-project-id` header
- `ModelApiKey`: `x-model-api-key` header
