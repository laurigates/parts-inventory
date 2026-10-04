"""Domain models for inventory items.

Attributes are kept as a free-form dict so a 'component' can carry
resistance/tolerance/package while a 'tool' carries bandwidth/channels etc.,
without a rigid column-per-property schema.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Kind(StrEnum):
    TOOL = "tool"
    COMPONENT = "component"


class Status(StrEnum):
    CONFIRMED = "confirmed"
    DEFERRED = "deferred"
    NEEDS_INPUT = "needs_input"


@dataclass
class Item:
    """A single inventory entry.

    `confidence` is 0.0-1.0 (recognition confidence). `attributes` holds
    kind-specific fields (e.g. {"resistance": "4.7k", "tolerance": "1%"} or
    {"bandwidth_mhz": 50, "channels": 3}).
    """

    name: str
    kind: Kind
    category: str = ""
    attributes: dict = field(default_factory=dict)
    quantity: int = 1
    confidence: float = 1.0
    image_path: str | None = None
    source_url: str | None = None
    status: Status = Status.CONFIRMED
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_row(self) -> dict:
        row = asdict(self)
        row["kind"] = str(self.kind)
        row["status"] = str(self.status)
        row["attributes"] = json.dumps(self.attributes, sort_keys=True)
        return row

    @classmethod
    def from_row(cls, row) -> Item:
        d = dict(row)
        d["kind"] = Kind(d["kind"])
        d["status"] = Status(d["status"])
        d["attributes"] = json.loads(d["attributes"]) if d.get("attributes") else {}
        return cls(**d)
