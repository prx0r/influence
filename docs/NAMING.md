# Naming — helping you think of names, then proving them

Two halves: open up (candidates) and close down (evidence). Never confuse them.

## Opening up: what makes a name good

Synthesized from the checker team's naming research (see sources below).
A name sits at the intersection of meaning, sound, memory,
distinctiveness, category fit, expandability, trust, visual potential,
human preference, agent interpretability, and legal ownability — and those
dimensions conflict. Suggestive names help recall of congruent info but
bias what gets encoded. Animal/common-word names buy memorability and
spend distinctiveness. The practical move: generate wide across packs
(default, tech, animals, nature, sanskrit-style), score narrow, keep the
shortlist small, and let evidence kill darlings.

Live generation: `POST /api/mine` on the checker (packs + scoring),
or chat `name <idea>` for the short interactive version.

## Closing down: the five honesty states

Borrowed from the namespace-intel model because it is the only honest one:

- TAKEN — authoritative evidence the object exists (RDAP/DNS/API hit).
- AVAILABLE — only a registration authority says this (registrar endpoint).
- NOT_FOUND — no public object; claimability UNPROVED. Never read as free.
- RESERVED / UNKNOWN — holds, WAFs, rate limits, ambiguity. Never a guess.

Rule: NOT_FOUND ≠ AVAILABLE. A 404 on a registry is not permission.

## The claim kit (one name, everywhere)

`GET /api/handles/:name` + MCP `claim_kit {domain}` on the checker, or chat
`check <name>` here: domain RDAP + DNS, registrar price compare, handle
namespace scan, one buy-link list. Evidence attached per verdict (source,
confidence, caveat). Failing closed on network error — UNKNOWN, never free.

## Sources (cmail, live service + research)

- Service: `https://domainnamechecker.tradesprior.workers.dev` —
  `/api/verify/:domain`, `/api/registrar/:domain`, `/api/handles/:name`,
  `POST /api/mine`, `POST /api/bulk-verify`, `POST /mcp` (claim_kit et al).
- Research: `cmail/domainnamechecker/docs/NAMING_SCIENCE.md`,
  `DOMAIN_ANIMAL_SCIENCE.md`, `socialintel.md`, `AVAILABILITY.md`.
