"""Generate the agent-readable inventory exports from the DB.

`inventory.md` is grouped and human/agent-friendly; `inventory.csv` is flat for
programmatic use. Both are regenerated wholesale — never hand-edited.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from .models import Item

CSV_FIELDS = [
    "id",
    "kind",
    "category",
    "name",
    "quantity",
    "attributes",
    "confidence",
    "status",
    "source_url",
    "image_path",
]


def _attrs_str(item: Item) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(item.attributes.items()))


def render_markdown(items: Iterable[Item]) -> str:
    items = list(items)
    grouped: dict[str, dict[str, list[Item]]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        grouped[str(it.kind)][it.category or "uncategorized"].append(it)

    out: list[str] = [
        "# Inventory",
        "",
        "_Generated from `inventory.db` — do not edit by hand._",
        "",
        f"Total items: {len(items)}",
        "",
    ]
    for kind in sorted(grouped):
        out.append(f"## {kind.capitalize()}s")
        out.append("")
        for category in sorted(grouped[kind]):
            out.append(f"### {category}")
            out.append("")
            out.append("| Name | Qty | Attributes | Confidence | Status |")
            out.append("|------|-----|------------|------------|--------|")
            for it in grouped[kind][category]:
                out.append(
                    f"| {it.name} | {it.quantity} | {_attrs_str(it) or '—'} "
                    f"| {it.confidence:.0%} | {it.status} |"
                )
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_csv(items: Iterable[Item]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for it in items:
        writer.writerow(
            {
                "id": it.id,
                "kind": str(it.kind),
                "category": it.category,
                "name": it.name,
                "quantity": it.quantity,
                "attributes": _attrs_str(it),
                "confidence": f"{it.confidence:.2f}",
                "status": str(it.status),
                "source_url": it.source_url or "",
                "image_path": it.image_path or "",
            }
        )
    return buf.getvalue()


def write_exports(items: Iterable[Item], out_dir: str | Path = "exports") -> None:
    items = list(items)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.md").write_text(render_markdown(items), encoding="utf-8")
    (out / "inventory.csv").write_text(render_csv(items), encoding="utf-8")
