# Domain Naming Science: Research-Backed Framework for Agent-Facing Products

> For a zero-awareness site in the agentic age, a semantically explicit or suggestive domain is probably more valuable than a purely invented brand name — but that should be measured as a cold-start discovery effect, not assumed as a universal branding rule.

---

## What the existing research says

There is surprisingly little rigorous domain-name research, but the strongest domain-specific study analyzed **more than one million domains** against realized website demand. Shorter domains, dictionary words, and avoiding punctuation were associated with better performance. The authors even found a positive association for numerals in their historical dataset, which is useful because it demonstrates why we should not encode naming folklore as truth. ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1714992))

There is also older direct domain research on immediate consumer trust. In one controlled survey using fictitious domains, keyword domains scored substantially above unfamiliar brandable domains on immediate trust. It is only one 100-person Danish study from 2011, so I would treat it as weak prior evidence rather than a universal result.

Broader brand-name research is stronger. Meaningful/suggestive names tend to be easier to remember and initially evaluated more positively; sound and conceptual fluency matter; and sound symbolism can communicate attributes such as size, speed, strength and weight. Crucially, non-meaningful names can improve relatively more with repeated exposure. ([Sage Journals](https://journals.sagepub.com/doi/10.1177/002224299806200105))

A very recent 2025 study of fruit brand names is especially relevant because it directly compared naming *types*: product/sensory-related names were preferred most, metaphorical names came next, and unusual spellings performed worst. That is almost the exact continuum we want to test for domains. ([Wiley Online Library](https://onlinelibrary.wiley.com/doi/full/10.1111/joss.70035))

Animals have some supporting branding research because they can activate archetypal associations, but there is **no convincing domain-specific evidence that animals are inherently superior names**. "Hound means search" is a plausible hypothesis. It should compete with `radar`, `probe`, `acorn`, `fetch`, `tinyget`, and `getdomain`, rather than receive a handcrafted animal bonus. ([Tuwhera Open Repository](https://openrepository.aut.ac.nz/bitstreams/85f44eaf-8a29-4027-948b-da84c13048df/download))

Concrete familiar words also have a general memory advantage over abstract words, which gives us a reasonable explanation for why animals, fruits, tools and physical objects may work so well: they come with dense existing semantic representations rather than requiring the user to learn a new token. ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1053811906006781))

---

## The naming taxonomy to test

| Family | Example shape | Cold-start agent prediction | Brand potential |
| --- | --- | ---: | ---: |
| Exact descriptive | `domainchecker` | Very high | Low |
| Action + object | `getpdf`, `checkdomain` | **Very high** | Medium |
| Suggestive compound | `tinyget` | **High** | **High** |
| Animal metaphor | `hound`, `mole` | Medium if metaphor fits | High |
| Tool/object | `radar`, `probe`, `relay` | Medium-high | High |
| Motion/verb | `fetch`, `seek`, `snap` | High for matching actions | High |
| Nature/fruit | `fig`, `plum`, `acorn`, `moss` | Low-medium | **Very high** |
| Person/place/myth | `atlas` | Medium | High |
| Invented phonosemantic | `velko` | Low | **Very high** |
| Semantic blend | Pokémon-style constructed word | Medium | **Very high** |
| Acronym/alphanumeric | `DNC`, `get42` | Variable | Medium |

The really interesting family is **suggestive compounds**.

`TinyGET` sits almost perfectly between:

```text
domainavailabilitychecker.com
       ↑
very understandable
terrible elasticity

tinyget.com
       ↑
understandable + brandable

velko.com
       ↑
very brandable
zero cold-start meaning
```

That is the Pareto frontier for many agent-facing products.

---

## The central experiment

Freeze a detailed `SiteIntent` **before the system generates a single name**.

For TinyTools, the frozen intent:

```json
{
  "purpose": "A public service exposing small deterministic APIs and MCP tools that agents and developers can invoke with minimal friction.",
  "primary_job": "When an agent needs a small capability, discover and execute the correct utility quickly.",
  "audiences": ["autonomous agents", "developers"],
  "constraints": {
    "tld": ".com",
    "zero_prior_brand_awareness": true
  }
}
```

The user should be encouraged to describe the purpose **very accurately**, because this object becomes permanent ground truth.

Then run multiple separate experiments.

---

## Experiment 1: actual agent search

This should be the strongest source of AgentSEO naming intelligence.

Don't say:

> What would you search?

Instead tell a fresh search-enabled model:

> Complete this task.

Give it the actual search tool.

Record:

```text
TASK
 ↓
search query #1
 ↓
results
 ↓
opens
 ↓
search query #2
 ↓
results
 ↓
opens
 ↓
...
 ↓
source selected
 ↓
tool used
 ↓
task success
```

The importance of this is directly supported by frontier research.

A 2026 study analyzing **14.44 million real agent search requests** found that agent search is iterative: agents reformulate queries and over half of newly introduced terms were grounded in evidence they had already retrieved. ([Hugging Face](https://huggingface.co/papers/2601.17617))

And the ACL 2026 survey treats search agents explicitly as sequential information-seeking systems rather than single-query retrievers. ([ACL Anthology](https://aclanthology.org/2026.acl-long.374/))

Permanent data becomes:

```text
intent_1483

GPT-*
1 "free api small utility functions"
2 "mcp utility tools api"
3 "agent callable api tools"

Claude-*
1 "simple MCP tools for common tasks"
2 "free API utilities agents"

Qwen-*
1 "AI agent tools API"
...
```

From 100,000 intents:

```text
"API"          appears in 68%
"tool"                     62%
"MCP"                      41%
"get"                      18%
"utility"                  16%
"function"                 14%
"service"                   8%
...
```

That's the AgentSEO naming corpus.

---

## Experiment 2: semantic inversion

Show **only**:

```text
tinyget.com
```

Ask an independent model:

> What do you predict this site does?

Then test:

```text
hound.com
fig.com
velko.com
gettool.com
tinyget.com
```

Measure:

**P(correct intent inferred | domain only)**

Call it `semantic_transmission`.

Animals aren't judged aesthetically. They are empirically tested.

Maybe:

```text
hound
→ tracking/searching 61%

mole
→ digging/searching 49%

radar
→ monitoring/discovery 78%

fig
→ food/agriculture 82%
→ software 4%
```

That immediately tells you whether the metaphor actually communicates the intended capability.

---

## Experiment 3: pure domain causal effect

**KEEP THE DESCRIPTION THE SAME.**

And title too.

And result position.

Everything except the domain.

```text
Task:
Find a service exposing small APIs and MCP tools.

A

tinyget.com
Small callable utilities for agents and developers.

B

velko.com
Small callable utilities for agents and developers.
```

Another trial:

```text
A velko.com
B tinyget.com
```

Fresh session.

Then again.

This isolates:

> **Does the hostname itself alter selection?**

LLM judges have measurable position bias, so order reversal/randomization is mandatory. ([arXiv](https://arxiv.org/abs/2406.07791))

Don't ask for `8.7/10`.

Collect:

```text
tinyget > velko
tinyget > gettool
gettool > hound
hound > velko
...
```

Fit Bradley–Terry.

That produces interpretable latent preference rather than arbitrary LLM ratings.

---

## Experiment 4: naming-family tournament

Generate matched candidates from:

```text
DESCRIPTIVE
ACTION_OBJECT
SUGGESTIVE_COMPOUND
ANIMAL
NATURE_FRUIT
TOOL_OBJECT
MOTION_VERB
MYTH_PLACE
INVENTED
PHONOSEMANTIC
CREATURE_COMPOSITIONAL
CONTRARIAN
```

DomainNameChecker does generation and availability.

AgentSEOLab does judgment.

Critically:

> A generator does **not** judge its own generated candidates in the same context.

Generation and evaluation must be separate calls/sessions.

---

## Experiment 5: metaphor/archetype mapping

Before using animals or objects, learn their embeddings experimentally.

For example:

```text
hound

tracking       0.94
persistence    0.89
search         0.83
speed          0.57
building       0.08
coordination   0.12
```

And:

```text
ant

coordination   0.93
small          0.91
work           0.86
distributed    0.71
search         0.21
```

Now if the intent is:

> distributed tiny workers

`ant` receives a strong **intent × archetype fit**.

If the product is:

> find information on the web

`hound` may beat it.

Animals don't receive an animal bonus. They receive **measured semantic alignment**.

Use exactly the same mechanism for:

```text
FRUIT: apple, fig, plum, lime
PLANTS: moss, fern, cedar, acorn
TOOLS: hammer, lens, probe, radar, relay
NATURAL PHENOMENA: cloud, flare, spark, wave, stream
MOTION: dash, fetch, seek, run, flow
MATERIALS: granite, silk, steel
PLACES: harbor, cove, field
CREATURES: fox, hound, ant, mole, raven, otter, falcon
```

This becomes a massive reusable **brand metaphor ontology**.

---

## Experiment 6: memory

Expose:

```text
tinyget.com
```

once.

Later ask the human/model to reconstruct it.

Measure:

```text
free recall
recognition
correct spelling
correct .com reconstruction
speech → domain reconstruction
```

This matters more than raw character length.

A seven-letter gibberish domain can be worse than a ten-letter meaningful one.

---

## Experiment 7: exposure curve

This answers the most important `gettool` versus `Velko` question.

Test at:

```text
exposure 0
exposure 1
exposure 3
exposure 7
```

Prior based on research:

```text
COLD START

gettool    █████
tinyget    ████▌
hound      ███
velko      █

AFTER BRAND EXPOSURE

gettool    █████
tinyget    █████
hound      ████▌
velko      ████
```

Meaningful names have an initial processing advantage, while meaningless names can improve more with repeated exposure. ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0148296304001602))

This distinction matters enormously for products without advertising. For those, optimize for **exposure zero**.

Apple could afford `Apple`. A tiny API launched into an agent ecosystem can't assume millions of exposures teaching everyone that an arbitrary fruit means computers.

---

## Therefore: suggestive compounds probably beat made-up words for cold-start agent products

Not because Google rewards keywords in domains. That's largely the wrong mechanism.

The hypothesis:

```text
agent has intent
    ↓
agent formulates lexical search
    ↓
retriever finds candidate
    ↓
agent sees candidate metadata
    ↓
domain reinforces task interpretation
    ↓
lower uncertainty
    ↓
agent investigates/calls it
```

Something like:

```text
getpdf.com
```

contains tremendous semantic information. But its **elasticity** is terrible.

```text
gettool.com
```

is broader.

And:

```text
tinyget.com
```

may have the best balance.

That's exactly what we should prove.

---

## Frontier agent-search research reinforces this

AgentSearchBench contains almost **10,000 real agents** and shows an important gap between description similarity and actual execution performance. Execution-aware signals improve retrieval/ranking. ([arXiv](https://arxiv.org/abs/2604.22436))

Translate that directly:

```text
NAME LOOKS RELEVANT
≠
SERVICE ACTUALLY WORKS
```

So AgentSEO should learn:

```text
P(agent discovers it)
×
P(agent selects it)
×
P(agent understands it)
×
P(tool succeeds)
```

not merely:

```text
embedding(domain, query)
```

DomainNameChecker can eventually tell someone:

> `getpdf.com` has excellent lexical discovery alignment, but the API behind candidate B has a stronger execution reputation.

Now we're getting into **agent marketplace naming + actual utility ranking**.

---

## The flywheel

```text
USER
"I need a .com for an MCP utility network"
             │
             ▼
       frozen SiteIntent
             │
             ├──────────────► actual agent search trials
             │                       │
             │                       ▼
             │                SEARCH LANGUAGE CORPUS
             │
             ▼
       candidate families
             │
             ▼
      DomainNameChecker
 availability + pricing
             │
             ▼
        AgentSEOLab
   randomized experiments
             │
       ┌─────┴─────┐
       ▼           ▼
    humans       models
       │           │
       └─────┬─────┘
             ▼
      naming evidence
             │
             ▼
          purchase
             │
             ▼
          website
             │
             ▼
         AgentSEO
             │
             ▼
 real search/citation/calls
             │
             └────────────► evidence library
```

Because the original intent is retained forever, you can eventually answer questions nobody else can answer:

- When agents are trying to find a **conversion API**, do action verbs improve selection?
- Do **animal metaphors** outperform object metaphors for monitoring products?
- Do GPT-family agents prefer explicit `api/tool/get` domains more strongly than Gemini-family agents?
- Do names that agents like also perform better with humans?
- Does the hostname matter much once `title + description + MCP metadata` are perfect?
- Which naming rules survive model upgrades?

That last one matters because generative search outputs have substantial cross-engine and temporal variation. ([ACL Anthology](https://aclanthology.org/2026.findings-acl.526/))

---

## DomainNameChecker should return experimental evidence, not a scalar score

Instead of a single score, return:

```json
{
  "domain": "tinyget.com",
  "static": {
    "length": 7,
    "dictionary_roots": ["tiny", "get"],
    "hyphen": false,
    "tld": "com"
  },
  "experimental": {
    "semantic_transmission": 0.84,
    "agent_pairwise_preference": 0.76,
    "human_recall": 0.81,
    "category_elasticity": 0.72,
    "field_visibility": null
  },
  "evidence": {
    "agent_trials": 840,
    "model_families": 7,
    "intents": 54,
    "last_tested": "...",
    "hypotheses": ["H-NAME-001", "H-NAME-006"]
  }
}
```

Then present a Pareto frontier:

```text
BEST FOR AGENT DISCOVERY
gettool.com

BEST FOR HUMAN MEMORY
hound.com

BEST BALANCED
tinyget.com

BEST LONG-TERM BRAND
velko.com
```

That is much more truthful.

---

## The first experiment to actually run

Use the TinyTools intent and generate roughly equal numbers of `.com` candidates from:

action-object, descriptive, suggestive compound, animal, tool/object, nature/fruit, motion verb, invented phonosemantic.

1. Collect real search traces **before showing any names**
2. Verify availability
3. Semantic inversion
4. Randomized hostname-only comparisons with the **exact same title and description**
5. Memory/archetype tests
6. Allow models to propose challengers
7. Rerun a fresh tournament

That gives you an evolutionary naming system where fitness is not "LLM says 9/10"; fitness is a vector of experimentally observed behavior.

The new experiment essentially turns the vision sentence — **intent → candidate → agent reaction → human reaction → price → selection → deployment → discoverability** — into a measurable research protocol.

---

## References

1. [Empirical Evidence for Domain Name Performance — SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1714992)
2. [The Effects of Brand Name Suggestiveness on Advertising Recall — Sage Journals](https://journals.sagepub.com/doi/10.1177/002224299806200105)
3. [Exploring the Effects of Fruit Brand Names on Consumer Preferences — Wiley](https://onlinelibrary.wiley.com/doi/full/10.1111/joss.70035)
4. [Animals, Archetypes, and Advertising (A3) — Tuwhera](https://openrepository.aut.ac.nz/bitstreams/85f44eaf-8a29-4027-948b-da84c13048df/download)
5. [The effect of word concreteness on recognition memory — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1053811906006781)
6. [Agentic Search in the Wild: 14M+ Real Search Requests — Hugging Face](https://huggingface.co/papers/2601.17617)
7. [A Survey of Large Language Model-Based Search Agents — ACL Anthology](https://aclanthology.org/2026.acl-long.374/)
8. [Judging the Judges: Position Bias in LLM-as-a-Judge — arXiv](https://arxiv.org/abs/2406.07791)
9. [Creating brand identity: evaluation of new brand names — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0148296304001602)
10. [AgentSearchBench: A Benchmark for AI Agent Search — arXiv](https://arxiv.org/abs/2604.22436)
11. [Characterizing Web Search in The Age of Generative AI — ACL Anthology](https://aclanthology.org/2026.findings-acl.526/)
