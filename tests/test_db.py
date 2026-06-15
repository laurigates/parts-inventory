import pytest

from parts_inventory.db import EMBED_DIM, Inventory
from parts_inventory.models import Item, Kind, Status


@pytest.fixture
def inv(tmp_path):
    with Inventory(tmp_path / "test.db") as inventory:
        yield inventory


def test_add_and_get_roundtrip(inv):
    item = Item(
        name="4.7k resistor",
        kind=Kind.COMPONENT,
        category="resistors",
        attributes={"resistance": "4.7k", "tolerance": "1%"},
        quantity=50,
        confidence=0.92,
    )
    item_id = inv.add(item)
    fetched = inv.get(item_id)

    assert fetched is not None
    assert fetched.name == "4.7k resistor"
    assert fetched.kind is Kind.COMPONENT
    assert fetched.attributes == {"resistance": "4.7k", "tolerance": "1%"}
    assert fetched.quantity == 50
    assert fetched.created_at is not None


def test_all_ordered(inv):
    inv.add(Item(name="ZT-703s", kind=Kind.TOOL, category="measurement"))
    inv.add(Item(name="10k", kind=Kind.COMPONENT, category="resistors"))
    names = [i.name for i in inv.all()]
    # components sort before tools (kind asc), so 10k first
    assert names == ["10k", "ZT-703s"]


def test_update_status(inv):
    item_id = inv.add(
        Item(name="mystery cap", kind=Kind.COMPONENT, status=Status.DEFERRED)
    )
    inv.update_status(item_id, "confirmed")
    assert inv.get(item_id).status is Status.CONFIRMED


def test_invalid_kind_rejected(inv):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        inv.conn.execute("INSERT INTO items (name, kind) VALUES ('x', 'gadget')")


def test_embedding_nearest_dedup(inv):
    base = [0.0] * EMBED_DIM
    a = base.copy()
    a[0] = 1.0
    b = base.copy()
    b[0] = 0.99  # very close to a
    c = base.copy()
    c[1] = 1.0  # orthogonal

    id_a = inv.add(Item(name="a", kind=Kind.COMPONENT), embedding=a)
    inv.add(Item(name="c", kind=Kind.COMPONENT), embedding=c)

    nearest = inv.nearest(b, k=1)
    assert nearest[0][0] == id_a  # closest match is the near-duplicate
