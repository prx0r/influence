# HydraDB integration

FinalBuilds uses the currently documented HydraDB HTTP client boundary:

```text
POST /v1/graphs/{graph_id}/query
Authorization: Bearer <token>
X-Graph-Namespace: <namespace>
Content-Type: application/json

{
  "cell_id": "cell-0",
  "query": "MATCH ..."
}
```

The adapter intentionally uses a generic OpenCypher model and keeps JSON payloads in string properties to minimize assumptions about HydraDB property-value compatibility.

## Why no HydraDB source is vendored

HydraDB is independently deployable, young and AGPL-3.0. Keeping a network boundary:

- lets FinalBuilds upgrade/pin Hydra independently;
- avoids coupling product code to Hydra internals;
- allows replacing the graph engine if requirements change;
- preserves event-log rebuildability.

## Local verification

`npm run hydra:smoke` is a genuine round-trip integration harness, but it requires Docker and access to GHCR. The regular unit suite tests the HTTP contract using a fake transport and requires no network or container runtime.
