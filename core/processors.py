"""Processors: bounded speculative computation. A processor takes typed
inputs plus a budget and returns proposed outputs, candidate evidence, and
a run record — never truth, never effects. Proposals become canonical only
when gates pass on them through receipts.transition elsewhere. A processor
that writes state, spends, sends, or mints authority is a protocol
violation, caught by tests."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProcessorSpec:
    name: str
    version: int
    input_schema: dict[str, Any]
    budget: dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    spec: str
    version: int
    outputs: dict[str, Any]
    evidence: list[dict[str, Any]]
    run: dict[str, Any]
    failure: str | None = None


_FORBIDDEN_KEYS = {"state_after", "grant", "signature", "receipt", "send", "spend", "mint"}


def run_processor(spec: ProcessorSpec, inputs: dict[str, Any],
                  fn: Callable[[dict], dict]) -> Proposal:
    """Execute fn under the propose-only contract. fn returns a dict; any
    forbidden key aborts the proposal (violation recorded, never passed)."""
    for key in inputs:
        if key not in spec.input_schema:
            raise ValueError(f"input {key} outside schema")
    out = fn(dict(inputs))
    if not isinstance(out, dict):
        raise ValueError("processor must return a dict")
    bad = _FORBIDDEN_KEYS & set(out)
    if bad:
        return Proposal(spec.name, spec.version, {}, [], {"worker": spec.name},
                        failure=f"forbidden keys: {sorted(bad)}")
    return Proposal(spec.name, spec.version,
                    outputs={k: v for k, v in out.items() if k != "evidence"},
                    evidence=list(out.get("evidence", [])),
                    run={"worker": spec.name, "version": spec.version,
                         "budget": spec.budget})


# Registry of first-class processors (propose-only by construction above).
def draft_writer(inputs: dict) -> dict:
    topic = inputs.get("topic", "")
    return {"draft": f"Draft about {topic} (edit me).",
            "evidence": [{"kind": "brief", "topic": topic}]}


def set_writer(inputs: dict) -> dict:
    premise = inputs.get("premise", "")
    techniques = inputs.get("techniques", [])
    return {"set": [f"Bit on {premise} via {t} (edit me)." for t in techniques],
            "evidence": [{"kind": "premise", "premise": premise}]}


PROCESSORS = {
    "draft.write": ProcessorSpec("draft.write", 1, {"topic": "str"}),
    "set.write": ProcessorSpec("set.write", 1, {"premise": "str", "techniques": "list"}),
}
PROCESSOR_FNS = {"draft.write": draft_writer, "set.write": set_writer}
