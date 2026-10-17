import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "report.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY,
    title  TEXT    NOT NULL,
    price  REAL    NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    url    TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS reports (
    id         INTEGER PRIMARY KEY,
    path       TEXT NOT NULL,  -- relative to the project root, e.g. reports/1.pdf
    created_at TEXT NOT NULL   -- ISO 8601 with the server's UTC offset
);
"""


def db_path() -> Path:
    return Path(os.environ.get("REPORT_DB", DEFAULT_DB))


def reports_dir() -> Path:
    return Path(os.environ.get("REPORTS_DIR", ROOT / "reports"))


def connect(path: Path | None = None) -> sqlite3.Connection:
    # isolation_level=None: no implicit transactions, so callers control BEGIN/COMMIT explicitly.
    conn = sqlite3.connect(path or db_path(), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE ... COMMIT, or ROLLBACK if the block raises. IMMEDIATE takes the write lock up front."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
