# Proofs, processors, modules — definitions (locked 2026-09-18)

Sources: `qprivately/SPEC.md` §8, `qpfinal/docs/QP_PROOFS_VS_PROCESSORS.md`.
Two terms are canonical. The third is ours — marked as such.

## Proof (canonical)

A proof says: this claim/transition satisfies a frozen evidence +
authority contract. Concretely: a TransitionReceipt, its independent
replay (`settle`), and its position in the hash chain (`verify_chain`).
Proofs freeze first; the verifier is versioned and builders cannot edit
it. Only the kernel mints; anyone with the law verifies. In code:
`law/acom/receipts.py`, `law/acom/store.py`, `validation/verify.py`.

## Processor (canonical, SPEC §8)

Speculative computation `(I,S,O,B,C,H) → (O',E',A',F,R)`: typed inputs,
working state, and a budget in; proposed outputs, *candidate* evidence,
*proposed* actions (which still require grants), typed failures, and a
measured run receipt out. A processor may produce things that help a
proof. It may never make them canonical merely by producing them.
Processors run behind a budget with observable effects; promotion is
decided by tournament + hidden tests, never self-certified. In code:
`qp/judges.py`, `core/rewards.py` (propose side), autopilot helpers,
checker mine/generate packs. A regex judge today and a Jev provider
tomorrow are the same processor contract.

## Module (OUR word — not in SPEC)

A state-owning structure above the kernel that moves state exclusively
through proofs. Modules commission processors; processors speed modules
up. The modules here: `core/` (graph + reconcile), `dash/` (plane +
rail), the studio factory (freaktown bridge, when it lands), the ledger
(spend/journal/vault). A module grows by adding leaves (one function +
gate + lens), never by forking; all its state changes are receipted or
they didn't happen. Promotion crosses upward by receipt only.

## Enforced, not just named (`qp/modules.py`)

Yes, module got added — as a derived concept, not a kernel edit. The
receipt shape is canonical (its id hashes every field), so membership
can't be a new field. Instead each module registers claim-domains plus
its gate set, and `scope_check` FAILS any receipt whose gates fall
outside its module: a provisioning receipt carrying foreign gates (or an
unregistered domain) is out of scope, loudly. Registry coverage over the
live receipt log is tested (`qp/test_modules.py`), so drift shows up as
red, not rot.

Live modules: **provision** (idea→endpoint chain), **studio** (content
factory), **ledger** (money + privacy), **venue** (reserved — no receipts
yet). Chat `modules` lists them; `product.get` carries each product's
module.
