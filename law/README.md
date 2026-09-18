# law — forked QP kernel, frozen

`law/acom/` is a byte-identical vendor of `qprivately/acom` at
`c18433a` (acom/0.1): one equation, seven objects, one TransitionReceipt,
append-only store, versioned gates, fail-closed grants.

Rules:
- NEVER edit files under `law/`. Change is a new pin, not a patch.
- Influence imports law first (`qp/law.py`), falls back to
  `QPRIVATELY_PATH` only if the vendor is missing.
- `law/test_pinned.py` fails on ANY byte drift vs the pinned source.
  Drift means re-pin deliberately (new commit id here + in SOURCES),
  never silent divergence.
- Everything influence-specific (judges, spend, privacy, adapters) lives
  in `qp/`, never in `law/`. Law settles; qp/ proposes.
