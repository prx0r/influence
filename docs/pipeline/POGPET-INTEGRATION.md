# pogpet ↔ influence integration

> 2026-10-10. Both repos grew complementary systems in parallel.
> Rule: **pogpet owns execution, influence owns orchestration.
> Read across the boundary, never duplicate.**

---

## Ownership map

| Concern | Owner | Reader | Sync |
|---|---|---|---|
| Transforms (`transforms/*.json`) | **pogpet** | influence reads | File path, no copy |
| Transform execution (`transform()`) | **pogpet** | influence calls via MCP/HTTP | — |
| Capability router + adapters | **pogpet** | influence never touches | — |
| Supplier technical truth (processes, upload rules, shipping) | **pogpet** `catalog/suppliers.json` | influence reads | By slug |
| Supplier relationship truth (status, emails, chase) | **influence** suppliers table | pogpet never touches | By slug |
| MCP tools (120, studio.*) | **pogpet** | influence calls via HTTP | — |
| Studio UI | **pogpet** (studio.oddhobb.com) | influence links out | — |
| Audit ledger, receipts, gates | **influence** | pogpet never touches | — |
| Goals, campaigns, budgets | **influence** | — | — |
| Product packs | **oddhobbies** | both read | — |
| Brand identity | **bgraph** | both read | — |

---

## Bridge 1: transforms (read pogpet's registry)

pogpet `transforms/*.json` format matches our VISUAL-PROVIDERS.md spec exactly:
`id, version, status, capability, references, instruction, preserve, output, qc, products`.

influence reads them directly:
```python
from pipeline.pogpet import load_transforms  # reads /root/pogpet/transforms/*.json
t = transforms["christmas_badge_v1"]
# t["qc"] → our image.py gates (identity, no_extra_text)
# t["products"] → which pack recipes can use it
```

No copy. If pogpet adds a transform, influence sees it.

## Bridge 2: suppliers (sync by slug, split fields)

```python
# pogpet owns: processes, upload_rules, shipping_known, site, account
# influence owns: status, emails, notes, chase, outreach
# join key: slug (jlc3dp→jlc? NO — keep both, map explicitly)
```

Slug map (`pipeline/pogpet.py SUPPLIER_MAP`):
```
pogpet jlc3dp     → influence jlc
pogpet printie    → influence printie
pogpet makerfabs  → influence makerfabs
pogpet ... (others map 1:1 or influence-only)
```

Sync direction:
- pogpet → influence: processes, shipping costs (for job packets + costs.py)
- influence → pogpet: nothing (relationship stays in dash)
- Dash supplier view shows BOTH: technical (from pogpet) + relationship (local)

## Bridge 3: MCP calls (dash → pogpet)

Dash never reimplements studio/transform/publish. It calls pogpet MCP over HTTP:

```
POST https://oddhobb.com/mcp  (or local :8799)
{
  "tool": "studio_options" | "design_create" | "transform_run" | ...,
  "args": {...},
  "actor": "influence-dash"
}
→ response → verify (G1-G5) → receipt → action row
```

Every MCP call is an audited action with cost. Same gates as everything else.

## Bridge 4: studio link-out

Dash Campaigns/Suppliers views link to `https://studio.oddhobb.com`
for visual work. No duplicate studio UI in influence.

---

## What NOT to do

- ❌ Copy transforms/*.json into influence
- ❌ Copy suppliers.json into influence
- ❌ Reimplement MCP tools in dash
- ❌ Build a second studio UI
- ❌ Write to pogpet files from influence (read-only across boundary)
- ❌ Write to influence DB from pogpet (each owns its store)

## Shared (read-only, neither owns)

- `oddhobbies/stores/*/listings/*.json` — product packs
- `bgraph/registry/brands/*.json` — identity + style
- Vault keys — both read via agent-vault, neither stores
