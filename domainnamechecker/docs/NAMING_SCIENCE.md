# Naming as Science: A Research Framework for Domain Name Intelligence

> Turning naming from a creative guessing exercise into a measurable, empirical discipline.

## The Core Insight

A good domain/brand name is not one-dimensional. It sits at the intersection of:

```text
MEANING
×
SOUND
×
MEMORY
×
DISTINCTIVENESS
×
CATEGORY FIT
×
EXPANDABILITY
×
TRUST
×
VISUAL / CHARACTER POTENTIAL
×
HUMAN PREFERENCE
×
AGENT INTERPRETABILITY
×
LEGAL OWNABILITY
```

And importantly, those dimensions can conflict.

---

## 1. Semantic suggestiveness is real — but there is a tradeoff

Classic branding research found that names which suggest the relevant product benefit improve recall of congruent information. But they can actually impair recall of unrelated benefits because the name biases what gets encoded. ([Sage Journals](https://journals.sagepub.com/doi/10.1177/002224299806200105))

So:

```text
PDFConvert.com
```

has enormous immediate category clarity but very little room to mean anything else.

Whereas:

```text
Otter
```

means almost nothing literally but has much greater potential to accumulate brand meaning.

This suggests a continuum:

```text
DESCRIPTIVE
│
│ domainchecker
│ pdfconvert
│ agenttools
│
├──────── suggestive
│ tinyget
│ cloudflare
│ fastmail
│
├──────── metaphorical
│ hound
│ beaver
│ raven
│
├──────── invented/compositional
│ pokemon-like names
│
└──────── abstract
    kodak-like arbitrary names
```

For utility/agent tools, **suggestive/metaphorical** is the sweet spot.

`tinyget` is interesting precisely because it does two things:

```text
tiny  → small/simple utility
get   → retrieve/call/request
```

without saying:

```text
autonomousagentmicroserviceutilitymarketplace.com
```

---

## 2. Processing fluency matters

Research distinguishes:

* **perceptual fluency** — easy to pronounce/read;
* **conceptual fluency** — easy to understand.

More fluent names tend to improve recognition and recall; conceptual meaning can compensate somewhat when the sound itself is less fluent. ([Taylor & Francis Online](https://www.tandfonline.com/doi/full/10.1080/10496491.2014.946203))

For domains this yields very testable variables:

```text
letters
syllables
phonemes
consonant clusters
pronunciation ambiguity
spelling ambiguity
homophones
keyboard complexity
speech-to-text ambiguity
```

For example, compare:

```text
tinyget
```

with:

```text
tgetx
```

The second is shorter, but probably much worse.

So **character count alone is a bad optimization target**.

We should measure something closer to:

> probability that someone hearing the name once can correctly type the domain.

That's an excellent experiment for the system.

---

## 3. Sound itself carries meaning

This is one of the strongest findings in naming research.

Phonemes aren't psychologically neutral.

Controlled research shows people infer product characteristics from the sounds appearing in invented brand names, often without consciously realizing they're doing so. ([OUP Academic](https://academic.oup.com/jcr/article-abstract/31/1/43/1812051))

A 2022 systematic framework found broad patterns where higher-frequency phonetic features—such as front vowels, fricatives and voiceless consonants—tend to convey different evaluation/potency associations from lower-frequency sounds such as back vowels, stops and voiced consonants. ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0148296322005458))

The famous underlying phenomenon is basically:

```text
kiki     → sharp / light / angular

bouba    → round / heavy / soft
```

And there are much subtler versions.

That means we can attach a **phonosemantic vector** to every candidate.

Something like:

```text
tinyget.com

perceived_size        small
perceived_speed       high
perceived_weight      low-medium
perceived_power       medium
perceived_friendliness medium-high
perceived_precision   high
```

Then experimentally validate it rather than assuming the linguistic literature transfers perfectly.

---

## 4. Pokémon naming is a giant natural experiment in synthetic brand naming

There is an actual corpus study of hundreds of Japanese Pokémon names.

Researchers found that **more voiced obstruents** in the names correlated with:

* larger Pokémon;
* heavier Pokémon;
* higher evolutionary stages;
* greater strength on several dimensions.

Longer names also correlated with size, weight, evolution and strength. ([PubMed Central (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6159826/))

Experiments then showed people can apply these patterns to **made-up Pokémon names they have never encountered**. ([Cambridge University Press](https://www.cambridge.org/core/journals/phonology/article/wugshaped-curve-in-sound-symbolism-the-case-of-japanese-pokemon-names/29309A586D66FF6287E7E72B9E2584D6))

And the pattern isn't only Japanese.

Experiments with English Pokémon-style names found that post-evolution/larger creatures were more likely to be assigned:

* longer names;
* `/a/` rather than `/i/`;
* `/u/` rather than `/i/`;
* particular consonant classes. ([Keio University](https://keio.elsevierpure.com/en/publications/how-to-express-evolution-in-english-pok%C3%A9mon-names/))

Brazilian Portuguese experiments found related sound-symbolic effects too, although the exact mappings differed by language. ([PubMed](https://pubmed.ncbi.nlm.nih.gov/31758426/))

Even more wonderfully specific:

> researchers tested whether **sibilants sound like flying**.

Japanese participants were more likely to associate names containing sibilants with flying-type creatures. ([Keio University](https://keio.elsevierpure.com/en/publications/do-sibilants-fly-evidence-from-a-sound-symbolic-pattern-in-pok%C3%A9mo/))

So yes: Pokémon naming is basically a giant natural experiment in synthetic brand naming.

---

## 5. The meta-system to copy (not Pokémon itself)

Actual Pokémon names and Pokémon itself are protected trademarks, and Pokémon explicitly identifies its character names as trademarks. So building commercial domains around actual Pokémon names is unnecessarily risky. ([Pokémon](https://www.pokemon.com/us/legal/information))

But the **generative principle** is excellent.

### Creature Naming Grammar

Suppose the thing is a web crawler.

First encode attributes:

```text
OBJECT
crawler

BEHAVIOUR
searches widely
follows trails
finds hidden things

PERSONALITY
persistent
fast
curious

SIZE
tiny utility

POWER
medium

ARCHETYPE
tracker / scavenger / hunter
```

Then generate from multiple conceptual families.

#### Literal concepts

```text
crawl
seek
track
find
fetch
```

#### Animal concepts

```text
hound
mole
ant
spider
fox
tern
gecko
```

#### Physical metaphors

```text
radar
probe
trail
net
beam
```

#### Phonetic targets

```text
short
quick
light
precise
```

#### Morphological mutations

```text
hound + fetch
mole + scan
tiny + seek
probe + fox
```

Then invent brand-like forms while retaining semantic residue.

This is basically **Pokémon-style generative naming**, except optimized for products.

---

## 6. Animals deserve their own ontology

There is marketing research specifically arguing that animal symbols automatically activate cultural/archetypal schemas and can thereby reinforce brand meaning and engagement. ([Taylor & Francis Online](https://www.tandfonline.com/doi/full/10.1080/0267257X.2013.765498))

That explains why tech branding repeatedly reaches for animals.

An animal gives you an extremely compressed semantic package.

| Animal  | Immediate conceptual bundle   |
| ------- | ----------------------------- |
| Hound   | search, tracking, persistence |
| Fox     | cleverness, agility           |
| Owl     | knowledge, observation        |
| Beaver  | building, industriousness     |
| Ant     | tiny, coordinated work        |
| Spider  | web, crawling, connections    |
| Mole    | digging, hidden information   |
| Raven   | intelligence, memory          |
| Falcon  | speed, vision                 |
| Gecko   | lightweight, agile            |
| Otter   | playful, nimble               |
| Turtle  | reliability, persistence      |
| Bee     | distributed work              |
| Magpie  | collecting/finds              |
| Octopus | many simultaneous operations  |

These aren't universal truths—the cultural meaning of animals varies—but they're rich priors.

We can build an `animal_ontology.json` with vectors like:

```json
{
  "hound": {
    "search": 0.97,
    "persistence": 0.93,
    "speed": 0.68,
    "friendliness": 0.71,
    "technical": 0.46,
    "builder": 0.12
  }
}
```

But again, **don't hand-author the final values**. Use them as hypotheses. Have humans and models experimentally map animal → attributes, then learn the vectors.

---

## 7. Concept → archetype experiments

We give the model a product intent:

> Service which continuously searches GitHub for emerging libraries and repositories.

Then ask:

```text
Which metaphor best represents this product?

hound
owl
mole
falcon
ant
beaver
raven
```

Across models and humans. Now we learn:

```text
GitHub discovery

hound       27%
raven       22%
mole        19%
falcon      14%
owl         11%
...
```

Then ask why, with structured codes:

```text
TRACKING
DISCOVERY
INTELLIGENCE
SPEED
COLLECTION
PERSISTENCE
```

Suddenly we have **Concept → archetype data**. That's upstream of domain generation.

---

## 8. Attribute inversion: what does the name itself suggest?

Instead of:

> What name fits this product?

run:

> What product do you think `Velko` provides?

No description. Then models infer:

```text
Velko

compute       28%
developer     20%
security      14%
analytics     11%
...
```

This measures the **semantic prior created by the name itself**.

Then compare it to intended meaning. Define:

```text
NAME SEMANTIC PRECISION

P(agent infers intended category | name alone)
```

For example:

```text
domainchecker.com       0.99
tinyget.com             0.71
velko.com                0.08
```

But also measure breadth:

```text
CATEGORY ELASTICITY

domainchecker.com       0.06
tinyget.com             0.83
velko.com                0.98
```

Now we expose a genuine naming tradeoff:

```text
                       immediately   future
                       understood    expandable

DomainChecker              █████       █
TinyGET                     ████        ████
Velko                       █           █████
```

---

## 9. Names can be too semantically strong

A highly suggestive name makes one idea easier to retrieve but can suppress unrelated ideas. ([Sage Journals](https://journals.sagepub.com/doi/10.1177/002224299806200105))

So the optimum isn't:

> maximum semantic relevance.

It's:

> **enough semantic relevance to bootstrap understanding without destroying future optionality.**

---

## 10. Brand anthropomorphism

Marketing psychology often models brands on two core social dimensions:

```text
WARMTH
"Does this entity have good intentions?"

COMPETENCE
"Can this entity actually do the job?"
```

The Brands as Intentional Agents work finds that these dimensions meaningfully describe how people perceive brands. ([DOI](https://doi.org/10.1002%2Farcp.1074))

Animals/characters are particularly useful because they make a brand easy to anthropomorphize.

For infrastructure tools we probably want:

```text
competence █████
warmth     ███
```

Not:

```text
evil-cyber-mega-terminator
```

and not:

```text
cuddly-baby-helper
```

---

## 11. The naming genome

Every candidate domain gets a feature vector.

```text
NAME GENOME
────────────────────────

ORTHOGRAPHY
characters
syllables
word boundaries
hyphens
digits
repeated characters

PHONOLOGY
phonemes
vowels
consonants
voicing
stops
fricatives
sibilants
sonority
stress
phonotactic probability

MORPHOLOGY
known morphemes
compound structure
blend structure
affixes

SEMANTICS
literalness
suggestiveness
metaphor
category match
benefit match

ARCHETYPE
animal
tool
motion
place
person
myth
material
natural phenomenon

PSYCHOLOGY
processing fluency
warmth
competence
potency
speed
size
friendliness
trust

BRAND
distinctiveness
memorability
expandability
visual potential
mascot potential

WEB
.com
length
speech-to-domain accuracy
typo risk
search ambiguity
existing entity collision

AGENT
intent inference
search-query overlap
tool association
API association
MCP association
agent preference

LEGAL
trademark collision
UDRP risk
existing company similarity
```

Then every interaction teaches the model which traits matter.

That's the real naming engine.

---

## 12. Existing automatic domain valuations mostly don't do this

Research into automatic domain-appraisal websites found significant credibility problems and noted that many supposedly "domain valuation" systems actually mix website-level metrics into their purported domain valuations. ([arXiv](https://arxiv.org/abs/1811.03415))

Instead of:

```text
tinyget.com
Estimated value: $4,831
```

which is basically nonsense precision, we output:

```text
tinyget.com

Semantic alignment       91
Human memorability       86
Agent recognition        94
Pronunciation            97
Category flexibility     88
Trademark risk           low
5-year registration      $...
```

with experiments/evidence behind each.

---

## 13. SEO distinction: ranking effect vs selection effect

Google's current guidance says keywords in the **domain itself have hardly any direct ranking effect**, and its exact-match-domain system specifically prevents query-stuffed domains from receiving excessive ranking credit. ([Google for Developers](https://developers.google.com/search/docs/appearance/ranking-systems-guide))

Google itself recommends concise, distinctive site names and discourages generic ones. ([Google for Developers](https://developers.google.com/search/docs/appearance/site-names))

So there are **two completely different effects**:

```text
SEARCH ENGINE RANKING EFFECT

vs

SEARCHER / AGENT SELECTION EFFECT
```

The domain's value is potentially:

```text
not
domain → algorithm ranking boost

but

domain
   ↓
human/agent interpretation
   ↓
selection
   ↓
memory
   ↓
links / mentions
   ↓
brand recognition
   ↓
discovery
```

We should measure them separately.

---

## 14. Seven generators for the domain engine

Instead of one LLM asking for names:

| Generator | Strategy | Question |
|-----------|----------|----------|
| 1 — DESCRIPTIVE | What exactly does it do? | "PDF signature tool" |
| 2 — SUGGESTIVE | What benefit does it provide? | "Sign in seconds" |
| 3 — ANIMAL | What creature behaves like this? | "Gecko" |
| 4 — OBJECT/METAPHOR | What physical thing behaves like this? | "Stamp" |
| 5 — PHONOSEMANTIC | Invent a word whose sound represents these attributes | "Velko" |
| 6 — POKÉMON-STYLE | Construct a novel compositional name from semantic roots + target phonology | "Sigleaf" |
| 7 — CONTRARIAN | Find names unlike the other six | Prevents convergence into one aesthetic |

Every generator competes in the same blinded tournament.

---

## 15. The naming experiment pipeline

```text
PRODUCT ATTRIBUTES
       ↓
phonological target
       ↓
candidate names (from 7 generators)
       ↓
BLIND TEST
       ↓
"What characteristics would you
expect something called X to have?"
       ↓
compare inferred attributes
against intended attributes
       ↓
SEMANTIC TRANSMISSION SCORE
```

Then instead of saying:

> "This sounds like a good name."

we can say:

> **83% of independent agents inferred concepts related to searching, retrieval or small utilities from this name without seeing the product description.**

That is a profoundly better naming criterion.

And it fits perfectly with the scientific infrastructure: **naming becomes another empirical AgentSEO experiment rather than a creative guessing exercise.**

---

## References

1. [Sound Symbolic Patterns in Pokémon Names — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6159826/)
2. [The Effects of Brand Name Suggestiveness on Advertising Recall — Sage Journals](https://journals.sagepub.com/doi/10.1177/002224299806200105)
3. [Meaning or Sound? The Effects of Brand Name Fluency — Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/10496491.2014.946203)
4. [Sound Idea: Phonetic Effects of Brand Names on Consumer Judgments — OUP](https://academic.oup.com/jcr/article-abstract/31/1/43/1812051)
5. [The connotative meanings of sound symbolism in brand names — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0148296322005458)
6. [A wug-shaped curve in sound symbolism: Japanese Pokémon names — Cambridge](https://www.cambridge.org/core/journals/phonology/article/wugshaped-curve-in-sound-symbolism-the-case-of-japanese-pokemon-names/29309A586D66FF6287E7E72B9E2584D6)
7. [How to express evolution in English Pokémon names — Keio](https://keio.elsevierpure.com/en/publications/how-to-express-evolution-in-english-pok%C3%A9mon-names/)
8. [Gotta Name'em All: Sound Symbolism in Pokémon Names in Brazilian Portuguese — PubMed](https://pubmed.ncbi.nlm.nih.gov/31758426/)
9. [Do sibilants fly? Evidence from a sound symbolic pattern in Pokémon names — Keio](https://keio.elsevierpure.com/en/publications/do-sibilants-fly-evidence-from-a-sound-symbolic-pattern-in-pok%C3%A9mo/)
10. [Legal Information — Pokemon.com](https://www.pokemon.com/us/legal/information)
11. [Animals, archetypes, and advertising (A3) — Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/0267257X.2013.765498)
12. [Social perception of brands: Warmth and competence — Wiley](https://doi.org/10.1002%2Farcp.1074)
13. [Credibility of Automatic Appraisal of Domain Names — arXiv](https://arxiv.org/abs/1811.03415)
14. [A Guide to Google Search Ranking Systems — Google](https://developers.google.com/search/docs/appearance/ranking-systems-guide)
15. [Site Names in Google Search — Google](https://developers.google.com/search/docs/appearance/site-names)
