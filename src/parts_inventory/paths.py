"""Where inventory data lives.

The DB, exports and reference images are user data, kept outside the code repo
(ADR-002). Resolution order: `PARTS_INVENTORY_DATA`, then
`$XDG_DATA_HOME/parts-inventory`, then `~/.local/share/parts-inventory`.
"""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    if override := os.environ.get("PARTS_INVENTORY_DATA"):
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
    return Path(xdg).expanduser() / "parts-inventory"
