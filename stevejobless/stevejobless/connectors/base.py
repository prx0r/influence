from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Observation:
    status: str
    message: str
    observed: dict[str, Any] = field(default_factory=dict)
    executor: str = "AUTO"
    human_title: str | None = None
    human_instructions: str | None = None
    human_url: str | None = None
    estimate_seconds: int = 60
    priority: int = 50


class Connector(Protocol):
    kind: str

    def observe(self, desired: dict[str, Any]) -> Observation: ...
