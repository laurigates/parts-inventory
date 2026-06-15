import pytest

from parts_inventory.db import Inventory
from parts_inventory.models import Item, Kind


@pytest.fixture
def inv(tmp_path):
    with Inventory(tmp_path / "d.db") as inventory:
        yield inventory


def test_matching_attributes_flagged_as_duplicate(inv):
    inv.add(
        Item(
            name="4.7k resistor",
            kind=Kind.COMPONENT,
            category="resistors",
            attributes={"resistance": "4.7k"},
        )
    )
    candidate = Item(
        name="resistor",
        kind=Kind.COMPONENT,
        category="resistors",
        attributes={"resistance": "4.7k"},
    )
    dups = inv.find_duplicates(candidate)
    assert len(dups) == 1
    assert dups[0].name == "4.7k resistor"


def test_different_value_not_duplicate(inv):
    inv.add(
        Item(
            name="4.7k",
            kind=Kind.COMPONENT,
            category="resistors",
            attributes={"resistance": "4.7k"},
        )
    )
    candidate = Item(
        name="10k",
        kind=Kind.COMPONENT,
        category="resistors",
        attributes={"resistance": "10k"},
    )
    assert inv.find_duplicates(candidate) == []


def test_different_kind_not_duplicate(inv):
    inv.add(Item(name="probe", kind=Kind.TOOL, category="misc"))
    candidate = Item(name="probe", kind=Kind.COMPONENT, category="misc")
    assert inv.find_duplicates(candidate) == []


def test_no_attributes_falls_back_to_name(inv):
    inv.add(Item(name="ZT-703s", kind=Kind.TOOL, category="measurement"))
    candidate = Item(name="zt-703s", kind=Kind.TOOL, category="measurement")
    assert len(inv.find_duplicates(candidate)) == 1
