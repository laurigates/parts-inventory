# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A vision-driven inventory of tools and electronic components for MCU/embedded
tinkering. Items are captured by passing them in front of the MacBook webcam; a
local vision model identifies them; entries are stored in SQLite and exported to
committed markdown/CSV so any Claude Code session can read what hardware is
actually on hand.

Full design: [docs/decisions/ADR-001-architecture.md](docs/decisions/ADR-001-architecture.md)

## Two consumers, two purposes

1. **The capture app** (humans) — webcam UI to add/defer/backfill items.
2. **Other Claude Code sessions** (agents) — read `exports/inventory.md` to
   suggest procedures using owned equipment and to break circuit-design ties
   toward parts already in stock.

## Architecture

| Layer | Choice |
|-------|--------|
| Canonical store | SQLite (`inventory.db`) — write-heavy small mutations |
| Dedup | attribute-based (primary); `sqlite-vec` ready but unused |
| Agent-readable exports | generated, committed `exports/inventory.{md,csv}` |
| Vision (local, Ollama) | `gemma3:4b` (stream/HUD), `gemma4:12b` (recognize) |
| App | FastAPI backend (`app/server.py`) + static frontend (`app/static/`) |
| Package manager | uv |
| Lint/format | ruff |
| Type checker | ty |

`inventory.db` is **gitignored** — the committed `exports/` are the shared
source of truth for agents. Regenerate exports after any DB change.

## Layout

```
parts-inventory/
├── app/                # FastAPI backend + browser frontend (vision, HUD)
├── src/                # core package: db schema, models, export generator
├── docs/decisions/     # ADRs
├── exports/            # generated, committed inventory.{md,csv}
└── images/             # reference photos (gitignored)
```

## Conventions

- **Conventional commits**: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`,
  `test:`, `ci:`.
- **TDD**: write the failing test first for data-layer logic (schema, export
  generation, dedup).
- **Exports are generated, never hand-edited** — edit the DB (or its writer),
  then regenerate.
- **uv** for everything Python: `uv run pytest`, `uv run ruff check`.

## Running the app

```bash
uv run uvicorn app.server:app --reload   # then open http://localhost:8000
uv run parts-inventory export            # regenerate exports/ from the DB
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
