"""FastAPI backend for the webcam capture app.

Endpoints back the low-friction workflow from ADR-001: stream a label for the
HUD, recognize an item on settle, check for duplicates, save (with a reference
image) or defer, backfill deferred items, and regenerate exports.

Run: uv run uvicorn app.server:app --reload
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from parts_inventory.db import Inventory
from parts_inventory.export import write_exports
from parts_inventory.models import Item, Kind, Status
from parts_inventory.paths import data_dir
from parts_inventory.vision import VisionClient

DATA_DIR = data_dir()
DB_PATH = DATA_DIR / "inventory.db"
IMAGES_DIR = DATA_DIR / "images"
EXPORTS_DIR = DATA_DIR / "exports"
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vision = VisionClient()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    yield
    await app.state.vision.aclose()


app = FastAPI(title="parts-inventory", lifespan=lifespan)


def _inv() -> Inventory:
    return Inventory(DB_PATH)


def _save_image(data: bytes) -> str:
    name = f"{uuid.uuid4().hex}.jpg"
    (IMAGES_DIR / name).write_bytes(data)
    return f"images/{name}"


@app.post("/api/stream")
async def stream(frame: UploadFile):
    """Fast HUD label for a single frame."""
    label = await app.state.vision.stream_label(await frame.read())
    return {"label": label}


@app.post("/api/recognize")
async def recognize(frame: UploadFile):
    """Settle-pass identification + duplicate check. Does not persist."""
    rec = await app.state.vision.recognize(await frame.read())
    candidate = Item(
        name=rec.name,
        kind=Kind(rec.kind)
        if rec.kind in (Kind.TOOL, Kind.COMPONENT)
        else Kind.COMPONENT,
        category=rec.category,
        attributes=rec.attributes,
        confidence=rec.confidence,
    )
    with _inv() as inv:
        dups = inv.find_duplicates(candidate)
    return {
        "recognition": rec.__dict__,
        "duplicates": [
            {"id": d.id, "name": d.name, "quantity": d.quantity} for d in dups
        ],
    }


@app.post("/api/items")
async def add_item(
    name: str = Form(...),
    kind: str = Form(...),
    category: str = Form(""),
    attributes_json: str = Form("{}"),
    quantity: int = Form(1),
    confidence: float = Form(1.0),
    source_url: str = Form(""),
    status: str = Form("confirmed"),
    image: UploadFile | None = None,
):
    import json

    image_path = _save_image(await image.read()) if image is not None else None
    item = Item(
        name=name,
        kind=Kind(kind),
        category=category,
        attributes=json.loads(attributes_json or "{}"),
        quantity=quantity,
        confidence=confidence,
        source_url=source_url or None,
        status=Status(status),
        image_path=image_path,
    )
    with _inv() as inv:
        item_id = inv.add(item)
    return {"id": item_id, "image_path": image_path}


@app.post("/api/items/{item_id}/status")
async def set_status(item_id: int, status: str = Form(...)):
    if status not in (s.value for s in Status):
        raise HTTPException(400, f"invalid status: {status}")
    with _inv() as inv:
        if inv.get(item_id) is None:
            raise HTTPException(404, "item not found")
        inv.update_status(item_id, status)
    return {"id": item_id, "status": status}


@app.get("/api/items")
async def list_items(status: str | None = None):
    with _inv() as inv:
        items = [i for i in inv.all() if status is None or str(i.status) == status]
    return [i.to_row() for i in items]


@app.post("/api/export")
async def export():
    with _inv() as inv:
        items = list(inv.all())
        write_exports(items, EXPORTS_DIR)
    return {"written": len(items)}


# Static frontend (mounted last so /api/* takes precedence).
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


@app.exception_handler(Exception)
async def _unhandled(request, exc):  # pragma: no cover - safety net
    return JSONResponse(status_code=500, content={"error": str(exc)})
