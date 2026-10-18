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
    id          INTEGER PRIMARY KEY,
    path        TEXT    NOT NULL,           -- relative to the project root, e.g. reports/1.pdf
    created_at  TEXT    NOT NULL,           -- ISO 8601 with the server's UTC offset
    report_date TEXT,                       -- the server's local date, YYYY-MM-DD
    forced      INTEGER NOT NULL DEFAULT 0  -- 1 = made with {"force": true}
);
"""

# Columns added in Stage 5, for a report.db created before them.
MIGRATIONS = {
    "report_date": "ALTER TABLE reports ADD COLUMN report_date TEXT",
    "forced": "ALTER TABLE reports ADD COLUMN forced INTEGER NOT NULL DEFAULT 0",
}

# At most one normal (not forced) report per day, enforced by the database itself.
ONE_REPORT_PER_DAY = (
    "CREATE UNIQUE INDEX IF NOT EXISTS one_report_per_day ON reports (report_date) WHERE forced = 0"
)


def db_path() -> Path:
    return Path(os.environ.get("REPORT_DB", DEFAULT_DB))


def reports_dir() -> Path:
    return Path(os.environ.get("REPORTS_DIR", ROOT / "reports"))


def connect(path: Path | None = None) -> sqlite3.Connection:
    # isolation_level=None: no implicit transactions, so callers control BEGIN/COMMIT explicitly.
    # timeout: a writer waits up to 30 s for another writer's lock (a render takes a second or two).
    conn = sqlite3.connect(path or db_path(), isolation_level=None, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(reports)")}
    for column, statement in MIGRATIONS.items():
        if column not in columns:
            conn.execute(statement)
    conn.execute(ONE_REPORT_PER_DAY)
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
