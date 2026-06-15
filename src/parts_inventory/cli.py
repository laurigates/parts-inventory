"""Command-line entry points.

`uv run parts-inventory export` regenerates exports/ from inventory.db. This is
the command to run after any DB change so the committed, agent-readable exports
stay in sync.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .db import Inventory
from .export import write_exports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parts-inventory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_export = sub.add_parser("export", help="Regenerate exports/ from the DB")
    p_export.add_argument("--db", default="inventory.db", type=Path)
    p_export.add_argument("--out", default="exports", type=Path)

    args = parser.parse_args(argv)

    if args.cmd == "export":
        with Inventory(args.db) as inv:
            items = list(inv.all())
            write_exports(items, args.out)
        print(f"Wrote {len(items)} items to {args.out}/inventory.{{md,csv}}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
