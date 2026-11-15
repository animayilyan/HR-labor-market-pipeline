"""Persist the three tables to SQLite (standard-library sqlite3) and Parquet."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

import polars as pl
import polars.selectors as cs

logger = logging.getLogger(__name__)

# Children are dropped first and created last so the foreign keys always resolve.
DDL: dict[str, str] = {
    "jobs": """
        CREATE TABLE jobs (
            slug              TEXT PRIMARY KEY,
            title             TEXT NOT NULL,
            company_name      TEXT NOT NULL,
            location          TEXT,
            remote            INTEGER NOT NULL CHECK (remote IN (0, 1)),
            url               TEXT NOT NULL,
            posted_at         TEXT NOT NULL,   -- ISO-8601 UTC, e.g. 2026-11-15T16:33:48Z
            seniority         TEXT NOT NULL,
            job_function      TEXT NOT NULL,
            tag_count         INTEGER NOT NULL,
            job_type_count    INTEGER NOT NULL,
            description_chars INTEGER NOT NULL
        )""",
    "job_tags": """
        CREATE TABLE job_tags (
            slug TEXT NOT NULL REFERENCES jobs (slug),
            tag  TEXT NOT NULL,
            PRIMARY KEY (slug, tag)
        )""",
    "job_types": """
        CREATE TABLE job_types (
            slug     TEXT NOT NULL REFERENCES jobs (slug),
            job_type TEXT NOT NULL,
            PRIMARY KEY (slug, job_type)
        )""",
}
TABLE_ORDER: list[str] = ["jobs", "job_tags", "job_types"]


def _to_sqlite_frame(df: pl.DataFrame) -> pl.DataFrame:
    """Convert types SQLite lacks: datetimes → ISO text, booleans → 0/1."""
    return df.with_columns(
        cs.datetime().dt.to_string("%Y-%m-%dT%H:%M:%SZ"),
        cs.boolean().cast(pl.Int8),
    )


def write_sqlite(db_path: Path, tables: dict[str, pl.DataFrame]) -> dict[str, int]:
    """Drop + recreate the tables and bulk-insert them in ONE transaction; return row counts."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)  # we manage the transaction ourselves
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")
        for name in reversed(TABLE_ORDER):
            conn.execute(f"DROP TABLE IF EXISTS {name}")
        for name in TABLE_ORDER:
            conn.execute(DDL[name])
            frame = _to_sqlite_frame(tables[name])
            placeholders = ", ".join("?" * frame.width)
            conn.executemany(
                f"INSERT INTO {name} ({', '.join(frame.columns)}) VALUES ({placeholders})",
                frame.iter_rows(),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return sqlite_counts(db_path)


def sqlite_counts(db_path: Path) -> dict[str, int]:
    """Return `SELECT COUNT(*)` for each table in the database."""
    with sqlite3.connect(db_path) as conn:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in TABLE_ORDER}


def write_parquet(out_dir: Path, tables: dict[str, pl.DataFrame]) -> dict[str, Path]:
    """Write each table to `<out_dir>/<name>.parquet`; return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name in TABLE_ORDER:
        paths[name] = out_dir / f"{name}.parquet"
        tables[name].write_parquet(paths[name])
    return paths


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a small JSON document (UTF-8, pretty-printed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    """Read a small JSON document; return `{}` if it does not exist."""
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
