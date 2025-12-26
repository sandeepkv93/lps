from __future__ import annotations

from pathlib import Path

from lps.storage.duckdb_store import Storage


def default_storage() -> Storage:
    return Storage(Path(".lps/lps.duckdb"))


__all__ = ["Storage", "default_storage"]
