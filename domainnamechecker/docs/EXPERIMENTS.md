# Fleet experiments

Use experiments for hypotheses such as:

- `llms.txt` structure;
- machine-readable alternate links;
- `describedby` metadata;
- schema/structured-data variants;
- page copy or information architecture;
- MCP discovery placement;
- pricing presentation;
- agent-visible docs organization.

## Procedure

1. Record research finding/evidence.
2. Register an experimental StandardVersion or Process.
3. Create experiment with explicit hypothesis and primary metric.
4. Assign a bounded cohort deterministically.
5. Apply treatment through normal desired-state deployment.
6. Collect observations for a predefined interval.
7. Produce experiment report.
8. Promote, reject or iterate.
9. Preserve the full historical experiment and treatment version.

Avoid running overlapping experiments on the same sites when they can confound the same metric unless the design explicitly accounts for interaction effects.
