# parts-inventory

Vision-driven inventory of tools and electronic components for MCU/embedded
tinkering — captured by waving items past the MacBook webcam, and made
**machine-readable to Claude Code** so the agent can suggest procedures that use
equipment you actually own and prefer circuit designs around parts already on
hand.

## Why

When working on MCU projects, an agent that doesn't know your equipment avoids
suggesting things like "scope this signal with your oscilloscope" or "use the
4.7k you already have." This inventory closes that gap: the committed
`exports/inventory.md` / `.csv` are read directly by any Claude Code session.

## How it works

Present an item to the webcam → a fast local vision model detects it and shows a
HUD guess with a confidence % → on settle, a stronger local model identifies it
and (optionally) web-searches exact part details → an embedding dedups against
what's already stored → save with a reference image, or defer ambiguous items to
a pile and backfill details by text at the end.

See [docs/decisions/ADR-001-architecture.md](docs/decisions/ADR-001-architecture.md)
for the full design.

## Stack

| Layer | Choice |
|-------|--------|
| Canonical store | SQLite (`inventory.db`); attribute-based dedup |
| Agent-readable exports | generated, committed `exports/inventory.{md,csv}` |
| Vision (local, via Ollama) | `gemma3:4b` (stream/HUD), `gemma4:12b` (recognize) |
| App | FastAPI backend + browser frontend (webcam, HUD, Web Speech, text input) |
| Package manager | uv |

## Run

```bash
uv run uvicorn app.server:app --reload   # http://localhost:8000
```

Needs a local Ollama with `gemma3:4b` and `gemma4:12b` pulled.

## Status

Data layer + vision/web app implemented and tested (19 tests). Vision verified
live against Ollama. Not yet driven with real inventory.
