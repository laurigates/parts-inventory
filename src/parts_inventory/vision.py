"""Ollama vision client for recognizing inventory items from webcam frames.

Two tiers (see ADR-001), both local via Ollama:
  - STREAM_MODEL: fast, for the continuous HUD "what is this?" loop.
  - RECOGNIZE_MODEL: stronger, for the settle-and-identify pass.

Recognition asks the model for structured JSON via Ollama's `format` schema so
the result maps directly onto an Item.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

import httpx

OLLAMA_URL = "http://localhost:11434"
STREAM_MODEL = "gemma3:4b"
RECOGNIZE_MODEL = "gemma4:12b"

# Ollama structured-output schema constraining the recognition response.
RECOGNITION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "kind": {"type": "string", "enum": ["tool", "component"]},
        "category": {"type": "string"},
        "attributes": {"type": "object"},
        "confidence": {"type": "number"},
        "needs_closer_look": {"type": "boolean"},
        "prompt_for_user": {"type": "string"},
        "bbox": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 4,
            "maxItems": 4,
        },
    },
    "required": ["name", "kind", "category", "confidence"],
}

STREAM_PROMPT = (
    "In 3 words or fewer, name the single electronics tool or component held up "
    "to the camera. If unclear, say 'unclear'."
)

RECOGNIZE_PROMPT = (
    "You are cataloguing an electronics workbench inventory. Identify the single "
    "tool or component shown. Classify kind as 'tool' (instruments, equipment) "
    "or 'component' (parts that go into circuits). Fill category (e.g. "
    "'resistors', 'measurement', 'microcontrollers') and attributes with "
    "kind-specific fields you can read (resistance, tolerance, package, voltage, "
    "bandwidth_mhz, channels, part_number). Set confidence 0-1. If a value is "
    "unreadable from this angle (e.g. resistor bands, chip markings), set "
    "needs_closer_look=true and put a short request in prompt_for_user. "
    "Also return bbox as [ymin, xmin, ymax, xmax] giving the item's bounding "
    "box in the image, each value normalized 0-1000 (0=top/left, 1000="
    "bottom/right)."
)


def _normalize_bbox(raw) -> list[float] | None:
    """Convert a model [ymin, xmin, ymax, xmax] (0-1000) box into a
    fractional [x, y, w, h] (each 0-1) for the frontend, or None if the box is
    missing/malformed. Local models emit unreliable boxes, so we clamp and
    drop degenerate ones rather than trust them blindly.
    """
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        ymin, xmin, ymax, xmax = (float(v) / 1000.0 for v in raw)
    except (TypeError, ValueError):
        return None
    x0, x1 = sorted((max(0.0, min(1.0, xmin)), max(0.0, min(1.0, xmax))))
    y0, y1 = sorted((max(0.0, min(1.0, ymin)), max(0.0, min(1.0, ymax))))
    w, h = x1 - x0, y1 - y0
    if w <= 0.0 or h <= 0.0:
        return None
    return [x0, y0, w, h]


@dataclass
class Recognition:
    name: str
    kind: str
    category: str
    attributes: dict
    confidence: float
    needs_closer_look: bool = False
    prompt_for_user: str = ""
    bbox: list[float] | None = None  # fractional [x, y, w, h], or None

    @classmethod
    def from_json(cls, data: dict) -> Recognition:
        return cls(
            name=data.get("name", "unknown"),
            kind=data.get("kind", "component"),
            category=data.get("category", ""),
            attributes=data.get("attributes") or {},
            confidence=float(data.get("confidence", 0.0)),
            needs_closer_look=bool(data.get("needs_closer_look", False)),
            prompt_for_user=data.get("prompt_for_user", ""),
            bbox=_normalize_bbox(data.get("bbox")),
        )


class VisionClient:
    def __init__(self, base_url: str = OLLAMA_URL, timeout: float = 120.0) -> None:
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _generate(
        self, model: str, prompt: str, image_b64: str, fmt: dict | None = None
    ) -> str:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "think": False,
        }
        if fmt is not None:
            payload["format"] = fmt
        resp = await self._client.post("/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")

    async def stream_label(self, image_bytes: bytes) -> str:
        """Fast, cheap label for the live HUD."""
        b64 = base64.b64encode(image_bytes).decode()
        text = await self._generate(STREAM_MODEL, STREAM_PROMPT, b64)
        return text.strip()

    async def recognize(self, image_bytes: bytes) -> Recognition:
        """Structured identification for the settle pass."""
        b64 = base64.b64encode(image_bytes).decode()
        text = await self._generate(
            RECOGNIZE_MODEL, RECOGNIZE_PROMPT, b64, fmt=RECOGNITION_SCHEMA
        )
        return Recognition.from_json(json.loads(text))
