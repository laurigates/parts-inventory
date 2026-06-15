import csv
import io

from parts_inventory.export import render_csv, render_markdown, write_exports
from parts_inventory.models import Item, Kind, Status


def sample():
    return [
        Item(
            id=1,
            name="ZT-703s oscilloscope",
            kind=Kind.TOOL,
            category="measurement",
            attributes={"bandwidth_mhz": 50, "channels": 1},
            confidence=0.95,
        ),
        Item(
            id=2,
            name="4.7k resistor",
            kind=Kind.COMPONENT,
            category="resistors",
            attributes={"resistance": "4.7k"},
            quantity=50,
            confidence=0.9,
        ),
        Item(
            id=3,
            name="mystery cap",
            kind=Kind.COMPONENT,
            category="capacitors",
            confidence=0.4,
            status=Status.NEEDS_INPUT,
        ),
    ]


def test_markdown_groups_by_kind_and_category():
    md = render_markdown(sample())
    assert "## Components" in md
    assert "## Tools" in md
    assert "### resistors" in md
    assert "4.7k resistor" in md
    assert "50%" not in md  # confidence formatting, not a stray value
    assert "90%" in md
    assert "Total items: 3" in md


def test_markdown_empty_attributes_dash():
    md = render_markdown([Item(name="thing", kind=Kind.TOOL, category="misc")])
    assert "| thing | 1 | — |" in md


def test_csv_is_flat_and_parseable():
    rows = list(csv.DictReader(io.StringIO(render_csv(sample()))))
    assert len(rows) == 3
    osc = next(r for r in rows if r["id"] == "1")
    assert osc["kind"] == "tool"
    assert "bandwidth_mhz=50" in osc["attributes"]
    assert osc["confidence"] == "0.95"


def test_write_exports_creates_both(tmp_path):
    write_exports(sample(), tmp_path)
    assert (tmp_path / "inventory.md").exists()
    assert (tmp_path / "inventory.csv").exists()
    assert "ZT-703s" in (tmp_path / "inventory.md").read_text()
