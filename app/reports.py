import sqlite3
from datetime import datetime
from pathlib import Path

from app.db import ROOT, transaction
from app.render import build_html, render_pdf
from app.report_data import get_all_books, get_report_data


def file_link(report_id: int) -> str:
    return f"/reports/{report_id}/file"


def to_public(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "created_at": row["created_at"], "path": row["path"], "file": file_link(row["id"])}


def generate_report(
    conn: sqlite3.Connection, reports_dir: Path, *, force: bool = False, now: datetime | None = None
) -> tuple[dict, bool]:
    """The whole pipeline in one call: query -> render -> store the file -> record its path.

    Once per day: if a report was already generated today (and force is False), it is returned instead of
    making a new one. Returns (report, created).

    Runs in one write-locked transaction, so two simultaneous requests are handled one after the other and
    the second one finds the first one's report. If rendering fails, the row is rolled back and no partial
    file is left.
    """
    now = now or datetime.now().astimezone()
    today = now.date().isoformat()
    with transaction(conn):
        if not force:
            existing = conn.execute(
                "SELECT id FROM reports WHERE report_date = ? AND forced = 0", (today,)
            ).fetchone()
            if existing:
                return get_report(conn, existing["id"]), False
        report_id = conn.execute(
            "INSERT INTO reports (path, created_at, report_date, forced) VALUES ('', ?, ?, ?)",
            (now.isoformat(timespec="seconds"), today, int(force)),
        ).lastrowid
        target = reports_dir / f"{report_id}.pdf"
        try:
            html = build_html(get_report_data(conn), get_all_books(conn), now.date())
            render_pdf(html, target)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        stored = target.relative_to(ROOT) if target.is_relative_to(ROOT) else target
        conn.execute("UPDATE reports SET path = ? WHERE id = ?", (str(stored), report_id))
    return get_report(conn, report_id), True


def get_report(conn: sqlite3.Connection, report_id: int) -> dict | None:
    row = conn.execute("SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,)).fetchone()
    return to_public(row) if row else None


def report_file(conn: sqlite3.Connection, report_id: int) -> Path | None:
    row = conn.execute("SELECT path FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        return None
    path = Path(row["path"])
    return path if path.is_absolute() else ROOT / path
