"""SQLite storage layer for the inventory.

The DB is the canonical store; `exports/` are generated from it. sqlite-vec is
loaded for embedding similarity (dedup / "already in inventory?"), but the
schema degrades gracefully when no embedding is provided.
"""

from __future__ import annotations

import sqlite3
import struct
from collections.abc import Iterator
from pathlib import Path

import sqlite_vec

from .models import Item

EMBED_DIM = 768  # gemma/minicpm embedding size; adjust to the model actually used.

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('tool', 'component')),
    category    TEXT NOT NULL DEFAULT '',
    attributes  TEXT NOT NULL DEFAULT '{}',
    quantity    INTEGER NOT NULL DEFAULT 1,
    confidence  REAL NOT NULL DEFAULT 1.0,
    image_path  TEXT,
    source_url  TEXT,
    status      TEXT NOT NULL DEFAULT 'confirmed'
                CHECK (status IN ('confirmed', 'deferred', 'needs_input')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

VEC_SCHEMA = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS item_embeddings USING vec0(
    item_id INTEGER PRIMARY KEY,
    embedding FLOAT[{EMBED_DIM}]
);
"""

_COLUMNS = (
    "id, name, kind, category, attributes, quantity, confidence, "
    "image_path, source_url, status, created_at, updated_at"
)


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


class Inventory:
    """Thin repository over a SQLite file. Use as a context manager."""

    def __init__(self, path: str | Path = "inventory.db") -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.executescript(VEC_SCHEMA)
        self.conn.commit()

    def __enter__(self) -> Inventory:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    # --- writes ---------------------------------------------------------

    def add(self, item: Item, embedding: list[float] | None = None) -> int:
        row = item.to_row()
        cur = self.conn.execute(
            """
            INSERT INTO items
                (name, kind, category, attributes, quantity, confidence,
                 image_path, source_url, status)
            VALUES
                (:name, :kind, :category, :attributes, :quantity, :confidence,
                 :image_path, :source_url, :status)
            """,
            row,
        )
        item_id = cur.lastrowid
        if item_id is None:
            raise RuntimeError("INSERT INTO items returned no rowid")
        if embedding is not None:
            self.conn.execute(
                "INSERT INTO item_embeddings (item_id, embedding) VALUES (?, ?)",
                (item_id, _pack(embedding)),
            )
        self.conn.commit()
        return item_id

    def update_status(self, item_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE items SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, item_id),
        )
        self.conn.commit()

    # --- reads ----------------------------------------------------------

    def get(self, item_id: int) -> Item | None:
        cur = self.conn.execute(
            f"SELECT {_COLUMNS} FROM items WHERE id = ?", (item_id,)
        )
        row = cur.fetchone()
        return Item.from_row(row) if row else None

    def all(self) -> Iterator[Item]:
        cur = self.conn.execute(
            f"SELECT {_COLUMNS} FROM items ORDER BY kind, category, name"
        )
        for row in cur:
            yield Item.from_row(row)

    def find_duplicates(self, item: Item) -> list[Item]:
        """Attribute-based dedup: existing items of the same kind+category whose
        identifying attributes match.

        This is the primary dedup path (embeddings are optional infra). A 4.7k
        resistor matches the existing 4.7k entry regardless of camera angle.
        Matching is conservative: same kind, same category, and every attribute
        the candidate carries must equal the stored value.
        """
        matches: list[Item] = []
        for existing in self.all():
            if existing.kind != item.kind:
                continue
            if existing.category != item.category:
                continue
            if item.attributes and all(
                existing.attributes.get(k) == v for k, v in item.attributes.items()
            ):
                matches.append(existing)
            elif not item.attributes and existing.name.lower() == item.name.lower():
                matches.append(existing)
        return matches

    def nearest(self, embedding: list[float], k: int = 3) -> list[tuple[int, float]]:
        """Return (item_id, distance) for the k nearest stored embeddings.

        Smaller distance == more similar. Used for dedup prompts.
        """
        cur = self.conn.execute(
            """
            SELECT item_id, distance
            FROM item_embeddings
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
            """,
            (_pack(embedding), k),
        )
        return [(int(r["item_id"]), float(r["distance"])) for r in cur]
