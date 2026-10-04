# ADR-002: Inventory data lives outside the code repo

Status: Accepted
Date: 2026-10-04
Supersedes: ADR-001 §1 (committed exports) and §4 phase 1 (exports read from the repo)

## Context

ADR-001 committed the generated `exports/inventory.{md,csv}` to this repo so any
Claude Code session could read them without infrastructure. The repo is now
published publicly on GitHub, and the inventory is personal data: a list of the
equipment and parts owned. The code is useful to share; the list is not.

## Decision

- All inventory data — `inventory.db`, `exports/`, `images/` — lives in a data
  directory outside the repo, resolved by `parts_inventory.paths.data_dir()`:
  1. `$PARTS_INVENTORY_DATA` if set
  2. `$XDG_DATA_HOME/parts-inventory` if `XDG_DATA_HOME` is set
  3. `~/.local/share/parts-inventory`
- The repo carries no data. `.gitignore` still lists `inventory.db`,
  `exports/` and `images/` as a guard against `PARTS_INVENTORY_DATA=.`.
- Agents read `<data dir>/exports/inventory.md`. Sessions in other repos learn
  that path from a user-global rule, not from this repo.

## Consequences

- Git history no longer versions the exports. The DB was already unversioned,
  so the data directory needs its own backup (Time Machine covers
  `~/.local/share` by default).
- Pointing `PARTS_INVENTORY_DATA` at a synced folder or a private repo is a
  configuration change, not a code change.
- ADR-001's Phase 2 (MCP server over the DB) is unaffected and would remove the
  need for agents to know the path at all.
