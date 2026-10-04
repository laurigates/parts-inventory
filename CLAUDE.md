# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A vision-driven inventory of tools and electronic components for MCU/embedded
tinkering. Items are captured by passing them in front of the MacBook webcam; a
local vision model identifies them; entries are stored in SQLite and exported to
markdown/CSV so any Claude Code session can read what hardware is actually on
hand. The data lives outside this repo (ADR-002).

Full design: [docs/decisions/ADR-001-architecture.md](docs/decisions/ADR-001-architecture.md),
data location: [ADR-002](docs/decisions/ADR-002-data-outside-repo.md)

## Two consumers, two purposes

1. **The capture app** (humans) — webcam UI to add/defer/backfill items.
2. **Other Claude Code sessions** (agents) — read
   `~/.local/share/parts-inventory/exports/inventory.md` to
   suggest procedures using owned equipment and to break circuit-design ties
   toward parts already in stock.

## Architecture

| Layer | Choice |
|-------|--------|
| Canonical store | SQLite (`inventory.db`) — write-heavy small mutations |
| Dedup | attribute-based (primary); `sqlite-vec` ready but unused |
| Data dir | `$PARTS_INVENTORY_DATA`, else `$XDG_DATA_HOME/parts-inventory`, else `~/.local/share/parts-inventory` (`paths.py`) |
| Agent-readable exports | generated `<data dir>/exports/inventory.{md,csv}` |
| Vision (local, Ollama) | `gemma3:4b` (stream/HUD), `gemma4:12b` (recognize) |
| App | FastAPI backend (`app/server.py`) + static frontend (`app/static/`) |
| Package manager | uv |
| Lint/format | ruff |
| Type checker | ty |

The repo holds **no inventory data**: `inventory.db`, `exports/` and `images/`
all live in the data dir. Regenerate exports after any DB change.

## Layout

```
parts-inventory/
├── app/                # FastAPI backend + browser frontend (vision, HUD)
├── src/                # core package: db schema, models, export generator
├── docs/decisions/     # ADRs
└── tests/              # pytest
```

## Conventions

- **Conventional commits**: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`,
  `test:`, `ci:`.
- **TDD**: write the failing test first for data-layer logic (schema, export
  generation, dedup).
- **Exports are generated, never hand-edited** — edit the DB (or its writer),
  then regenerate.
- **just** for tasks (`just --list`); **uv** underneath for everything Python.
- `just check` (ruff, ruff format, ty, pytest) must pass before committing;
  pre-commit and CI run the same gates.

## Running the app

```bash
just dev      # uvicorn with reload, then open http://localhost:8000
just export   # regenerate <data dir>/exports/ from the DB
```

Requires a local Ollama (`http://localhost:11434`) with `gemma3:4b` and
`gemma4:12b` pulled. Embeddings need the server started with `--embeddings`
(currently not enabled) — until then dedup is attribute-based, which is fine.

## Build order

1. **Data layer** (done) — SQLite schema, models, export generator, dedup.
2. **Vision pipeline + web app** (done) — Ollama client (gemma3 stream /
   gemma4 recognize), FastAPI endpoints, webcam HUD frontend with defer pile.
3. (Later) MCP query server; cloud fine-print escalation; standardized
   "product photo" images; editing deferred-item fields (v1 confirms status
   only); enable `--embeddings` for visual dedup.
