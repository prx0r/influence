from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    name: str
    domain: str | None = None
    passport: dict[str, Any] = Field(default_factory=dict)


class ProjectPatch(BaseModel):
    name: str | None = None
    domain: str | None = None
    passport: dict[str, Any] | None = None


class ActionComplete(BaseModel):
    done: bool = True
