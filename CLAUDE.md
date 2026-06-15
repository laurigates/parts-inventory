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
| Embeddings | `sqlite-vec` extension (dedup / similarity) |
| Agent-readable exports | generated, committed `exports/inventory.{md,csv}` |
| Vision (local, Ollama) | `minicpm5` (stream/HUD), `gemma4:12b` (recognize) |
| App | FastAPI backend + browser frontend |
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

## Build order (current)

1. **Data layer** (in progress) — SQLite schema, models, export generator.
   Testable without a camera.
2. Vision pipeline + web app on top.
3. (Later) MCP query server; cloud fine-print escalation; standardized
   "product photo" images.
