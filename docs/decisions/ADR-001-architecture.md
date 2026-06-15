# ADR-001: Architecture

Status: Accepted
Date: 2026-06-15

## Context

A vision-driven inventory of tools and electronic components for MCU/embedded
tinkering. Primary goal: make the inventory **machine-readable to Claude Code**
so that, when working on MCU projects, the agent can:

1. Suggest procedures that depend on equipment actually owned (e.g. "use the
   ZT-703s oscilloscope to check this signal" instead of avoiding the
   suggestion).
2. Use owned components as a **tie-breaker** in circuit design — prefer a design
   that uses parts already on hand over one requiring new purchases.

Secondary goal: capture the inventory with **minimal user friction** — ideally
just passing items in front of the MacBook webcam.

## Decisions

### 1. Storage: SQLite (canonical) + committed markdown/CSV exports

- `inventory.db` (SQLite) is the single source of truth. Handles the
  write-heavy small-mutation pattern (add / defer / backfill / update
  confidence), embeddings, and image references cleanly.
- Embeddings via the `sqlite-vec` extension for "have I already added this?"
  dedup and similarity search.
- `exports/inventory.md` and `exports/inventory.csv` are **generated** from the
  DB and committed to git. Any Claude Code session reads these directly — zero
  infra needed to consume the inventory.
- Rejected DuckDB: OLAP/columnar, optimized for analytical scans over large
  tables; our pattern is transactional small-row mutation on a tiny dataset.
  SQLite is the better fit. (DuckDB can read the SQLite file later if heavy
  analytics are ever wanted.)

### 2. Vision: local-first via Ollama, tiered models

All recognition runs locally on the Mac via Ollama. Tiers:

| Tier | Model | Role |
|------|-------|------|
| Stream | `openbmb/minicpm5` (688 MB) | Fast continuous "what am I looking at" detection for the live HUD |
| Recognize | `gemma4:12b` (multimodal) | Primary identification + reasoning when an item settles in frame |
| Escalate (later) | Cloud (Gemini/Claude vision) | Optional fine-print reads (SMD codes, resistor bands) on low confidence |

- Web search (for exact part details / datasheets) hits the internet regardless.
- Verify each model's vision capability with a smoke test before wiring in.

### 3. App platform: local web app

- Python backend (FastAPI) + browser frontend.
- `getUserMedia` for the webcam, canvas HUD overlay, Web Speech API for audio
  prompts ("show me the resistor closer"), plain text input for fields vision
  can't resolve.
- Cross-platform, fast to iterate, extends naturally to an MCP server.
- Trade-off: cannot access macOS Continuity "Desk View" (a system camera, not a
  programmable API). Acceptable loss.

### 4. Consumption: committed files now, MCP server later

- Phase 1: generated markdown/CSV in the repo, read directly by any session.
- Phase 2 (earned, not upfront): wrap the DB in an MCP server for structured
  queries ("do I have a 4.7k resistor?", "what can measure a 40 MHz signal?").

## Item lifecycle (low-friction capture)

```
present item to camera
  -> stream model detects an object, HUD shows best guess + confidence %
  -> on settle, recognize model identifies it
  -> compute embedding; if similar to an existing entry -> "already in
     inventory, add anyway?"
  -> if enough info: save (entry graded with confidence %) + reference image
  -> if NOT enough info (e.g. resistor value unreadable):
       audio/text prompt for a closer/different angle
       OR user defers: set item aside in a "pile", show next item
  -> deferred items get details backfilled at the end via text input
```

This makes the happy path "wave items past the camera; pile up the ambiguous
ones; fill those in at the end."

## Data model (initial sketch)

- `items`: id, kind (tool|component), name, category, attributes (JSON:
  e.g. resistance, tolerance, package, voltage), quantity, confidence,
  image_path, source_url, created_at, updated_at, status
  (confirmed|deferred|needs_input).
- `embeddings`: item_id, vector (via sqlite-vec).

## Future improvements (out of scope for v1)

- "Product photo" standardized images via an image-editing model, browsable in
  the app.
- MCP server (Phase 2 above).
- Cloud escalation tier for fine print.
