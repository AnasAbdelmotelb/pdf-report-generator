from collections.abc import Iterator
from sqlite3 import Connection
from typing import Annotated

from fastapi import Body, Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from app.db import connect, reports_dir
from app.reports import generate_report, get_report, report_file

app = FastAPI(title="PDF report generator")


def get_conn() -> Iterator[Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[Connection, Depends(get_conn)]


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    force: bool = False  # true = make a new report even if one already exists today


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Plain `def` endpoints: FastAPI runs them in a worker thread, which Playwright's sync API needs.
@app.post("/reports", status_code=201)
def create_report(
    conn: Conn, response: Response, request: Annotated[ReportRequest | None, Body()] = None
) -> dict:
    """Runs the whole pipeline inside the request. Answers with the id and a link, never the bytes.

    201 = a new report was made; 200 = today's existing report is returned (asking twice gives one file).
    """
    force = request.force if request else False
    report, created = generate_report(conn, reports_dir(), force=force)
    if not created:
        response.status_code = 200
    return {"id": report["id"], "file": report["file"]}


@app.get("/reports/{report_id}")
def read_report(report_id: int, conn: Conn) -> dict:
    report = get_report(conn, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/reports/{report_id}/file")
def download_report(report_id: int, conn: Conn) -> FileResponse:
    """The only endpoint that moves the PDF's bytes: streamed from disk."""
    path = report_file(conn, report_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report file is missing on disk")
    return FileResponse(path, media_type="application/pdf", filename=f"report-{report_id}.pdf")
