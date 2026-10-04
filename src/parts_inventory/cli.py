"""Command-line entry points.

`uv run parts-inventory export` regenerates exports/ from inventory.db, both in
the data directory (see paths.py). Run it after any DB change so the
agent-readable exports stay in sync.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .db import Inventory
from .export import write_exports
from .paths import data_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parts-inventory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_export = sub.add_parser("export", help="Regenerate exports/ from the DB")
    p_export.add_argument("--db", default=data_dir() / "inventory.db", type=Path)
    p_export.add_argument("--out", default=data_dir() / "exports", type=Path)

    args = parser.parse_args(argv)

    if args.cmd == "export":
        args.db.parent.mkdir(parents=True, exist_ok=True)
        with Inventory(args.db) as inv:
            items = list(inv.all())
            write_exports(items, args.out)
        print(f"Wrote {len(items)} items to {args.out}/inventory.{{md,csv}}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
