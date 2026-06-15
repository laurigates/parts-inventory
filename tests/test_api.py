"""API smoke tests. The vision client is replaced with a fake so tests never
hit Ollama; they exercise the HTTP wiring, persistence, and dedup path.
"""

import pytest
from fastapi.testclient import TestClient

import app.server as server
from parts_inventory.vision import Recognition


class FakeVision:
    async def stream_label(self, image_bytes):
        return "fake label"

    async def recognize(self, image_bytes):
        return Recognition(
            name="4.7k resistor",
            kind="component",
            category="resistors",
            attributes={"resistance": "4.7k"},
            confidence=0.9,
        )

    async def aclose(self):
        pass


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DB_PATH", tmp_path / "api.db")
    monkeypatch.setattr(server, "IMAGES_DIR", tmp_path / "images")
    monkeypatch.setattr(server, "EXPORTS_DIR", tmp_path / "exports")
    with TestClient(server.app) as c:
        c.app.state.vision = FakeVision()
        yield c


def _frame():
    return {"frame": ("f.jpg", b"\xff\xd8\xff", "image/jpeg")}


def test_stream_label(client):
    r = client.post("/api/stream", files=_frame())
    assert r.status_code == 200
    assert r.json()["label"] == "fake label"


def test_recognize_then_add_then_dedup(client):
    r = client.post("/api/recognize", files=_frame())
    assert r.json()["recognition"]["name"] == "4.7k resistor"
    assert r.json()["duplicates"] == []  # nothing stored yet

    r = client.post(
        "/api/items",
        data={
            "name": "4.7k resistor",
            "kind": "component",
            "category": "resistors",
            "attributes_json": '{"resistance": "4.7k"}',
        },
    )
    assert r.status_code == 200
    item_id = r.json()["id"]

    # now recognition should flag the stored item as a duplicate
    r = client.post("/api/recognize", files=_frame())
    dups = r.json()["duplicates"]
    assert len(dups) == 1 and dups[0]["id"] == item_id


def test_defer_and_list(client):
    client.post(
        "/api/items",
        data={"name": "mystery", "kind": "component", "status": "deferred"},
    )
    r = client.get("/api/items", params={"status": "deferred"})
    assert len(r.json()) == 1


def test_export_writes_files(client, tmp_path):
    client.post("/api/items", data={"name": "x", "kind": "tool"})
    r = client.post("/api/export")
    assert r.json()["written"] == 1
    assert (tmp_path / "exports" / "inventory.md").exists()
