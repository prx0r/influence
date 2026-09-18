# Modules and processors — the stack as an extended QP

QP proper ends at the receipt. Everything above is either a **module**
(a huge structure that owns state and moves it through receipts) or a
**processor** (a way to speed a module up — proposes, never settles).

```
law/            the forked kernel (frozen, drift-guarded)
  └─ modules    core/ (graph + reconcile), dash/ (plane + rail),
                studio factory (freaktown bridge, when it lands),
                ledger (spend/journal/vault)
       └─ processors  qp/judges.py (typed answers), core/rewards.py
                (ingest + reweight proposals), autopilot loop,
                future qpfinal-style processor SDK packs
```

Rules, same as QP's:

- Modules move state only through receipts. No direct writes that bypass
  reconcile → evidence → gates → receipt → settle.
- Processors never mint truth, hold no state, and are replaceable: a
  regex judge today, a Jev provider tomorrow, same contract.
- A module grows by adding leaves (one function + gate + lens), never by
  forking. A processor grows by getting faster/smarter behind the same
  typed interface.
- Promotion crosses the boundary upward by receipt only: a processor's
  proposal becomes module state iff gates pass on it.
