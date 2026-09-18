# Architecture decisions

## 1. Event truth versus graph truth

Every meaningful lifecycle transition is appended as an event first. The graph is updated immediately as a projection. This makes the graph disposable and allows future graph-engine changes.

## 2. Generic graph schema

All nodes use the `Entity` label and all edges use `REL`. Semantic type/kind lives in properties. This avoids requiring schema changes every time the factory learns a new entity category.

## 3. Process provenance

A `Process` is a versioned method/strategy. A `ProcessRun` is one invocation with concrete parameters, model, inputs, outputs, costs and status. Never overwrite a process definition to represent a new method; create a new version.

Suggested stages:

```text
idea-generation
baseline-test
market-scout
research
domain-selection
architecture
oss-composition
implementation
review
deployment
seo
agent-discovery
pricing
maintenance
```

## 4. Observations

An observation should be immutable and timestamped. Recommended common fields:

```text
id
sensor_id
subject_id
metric
value
unit
observed_at
dimensions
experiment_id?
standard_version_id?
artifact_digest?
```

Do not overwrite yesterday's latency with today's latency. Add a new observation.

## 5. Experiments

Experiment assignment is deterministic. Treatment changes should be represented as desired-state overrides and applied by the same normal deployment path as fleet standards, never by hidden one-off mutations.

## 6. Learning

There are two learning modes:

**Observational:** rank pipeline processes by downstream outcomes. Useful for prioritization, not proof.

**Experimental:** change one defined treatment across a controlled cohort and compare outcomes. Use this before promoting SEO/agent-discovery hypotheses into required standards.

## 7. HydraDB boundary

Keep all graph-specific behavior behind `GraphStore`. This implementation supplies memory and Hydra HTTP adapters. Do not allow application code to scatter raw Cypher throughout the controller.
