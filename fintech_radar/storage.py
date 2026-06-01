import hashlib
import sqlite3
from pathlib import Path

from .models import FeedItem


class Store:
    def __init__(self, path: str):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    link TEXT NOT NULL,
                    summary TEXT,
                    published_at TEXT,
                    source_type TEXT,
                    categories TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def insert_item(self, item: FeedItem) -> bool:
        item_id = fingerprint(item)
        published = item.published_at.isoformat() if item.published_at else None
        categories = ",".join(item.categories)

        with self.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO items (
                        id, source_name, source_url, title, link, summary,
                        published_at, source_type, categories
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        item.source_name,
                        item.source_url,
                        item.title,
                        item.link,
                        item.summary,
                        published,
                        item.source_type,
                        categories,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def has_item(self, item: FeedItem) -> bool:
        if not self.path.exists():
            return False
        item_id = fingerprint(item)
        with self.connect() as conn:
            row = conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone()
        return row is not None


def fingerprint(item: FeedItem) -> str:
    stable = item.link.strip().lower() or f"{item.source_name}:{item.title}".lower()
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
