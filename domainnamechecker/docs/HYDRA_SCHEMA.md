# Domain Intelligence Graph Schema

## Entity Types

### Domain
```cypher
CREATE (d:Entity {
  kind: 'domain',
  name: 'example.com',
  tld: 'com',
  label: 'example',
  status: 'AVAILABLE',  // AVAILABLE | TAKEN | PREMIUM | UNAVAILABLE | UNSUPPORTED | UNVERIFIED
  first_checked: datetime(),
  last_checked: datetime(),
  check_count: 1,
  registrar_links: 'json_array',
  proof: 'json_object'
})
```

### Check
```cypher
CREATE (c:Entity {
  kind: 'check',
  domain: 'example.com',
  status: 'AVAILABLE',
  source: 'cf_registry',  // cf_registry | rdap | validation
  authoritative: true,
  latency_ms: 137,
  checked_at: datetime(),
  proof: 'json_object'
})
```

### Experiment
```cypher
CREATE (e:Entity {
  kind: 'experiment',
  name: 'agent-preference-v1',
  hypothesis: 'Agents prefer short, memorable .com domains',
  primary_metric: 'selection_probability',
  status: 'running',  // design | running | completed | rejected
  created_at: datetime(),
  cohort_size: 100
})
```

### Observation
```cypher
CREATE (o:Entity {
  kind: 'observation',
  experiment_id: 'exp-001',
  domain: 'example.com',
  agent_model: 'gpt-4',
  metric: 'selection_probability',
  value: 0.73,
  observed_at: datetime()
})
```

### AgentPreference
```cypher
CREATE (a:Entity {
  kind: 'agent_preference',
  domain: 'example.com',
  agent_model: 'gpt-4',
  preference_score: 0.85,
  last_observed: datetime(),
  observation_count: 12
})
```

## Relationships

```
Domain -[:CHECKED_AT]-> Check
Domain -[:PREFERRED_BY]-> AgentPreference
Experiment -[:OBSERVED_IN]-> Observation
Domain -[:PART_OF]-> Experiment
```

## Queries

### Get domain history
```cypher
MATCH (d:Entity {kind: 'domain', name: $domain})
OPTIONAL MATCH (d)-[:CHECKED_AT]->(c:Entity {kind: 'check'})
RETURN d, collect(c) AS checks
ORDER BY c.checked_at DESC
```

### Get domain recommendations
```cypher
MATCH (d:Entity {kind: 'domain', status: 'AVAILABLE'})
WHERE d.name CONTAINS $concept
OPTIONAL MATCH (d)-[:PREFERRED_BY]->(a:Entity {kind: 'agent_preference'})
RETURN d, a
ORDER BY a.preference_score DESC
LIMIT 10
```

### Get experiment results
```cypher
MATCH (e:Entity {kind: 'experiment', name: $name})
MATCH (e)-[:OBSERVED_IN]->(o:Entity {kind: 'observation'})
RETURN e, collect(o) AS observations
```

## Event Schema

```json
{
  "event_type": "domain_checked",
  "payload": {
    "domain": "example.com",
    "status": "AVAILABLE",
    "source": "cf_registry",
    "authoritative": true,
    "latency_ms": 137,
    "checked_at": "2026-08-22T..."
  }
}
```

```json
{
  "event_type": "agent_preference_observed",
  "payload": {
    "domain": "example.com",
    "agent_model": "gpt-4",
    "preference_score": 0.85,
    "observed_at": "2026-08-22T..."
  }
}
```

```json
{
  "event_type": "experiment_created",
  "payload": {
    "experiment_id": "exp-001",
    "name": "agent-preference-v1",
    "hypothesis": "Agents prefer short, memorable .com domains",
    "created_at": "2026-08-22T..."
  }
}
```
