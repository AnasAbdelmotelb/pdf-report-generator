import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.main import app
from scripts.seed import seed


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A seeded throwaway database and reports folder, so tests never touch report.db or reports/."""
    db, reports = tmp_path / "report.db", tmp_path / "reports"
    monkeypatch.setenv("REPORT_DB", str(db))
    monkeypatch.setenv("REPORTS_DIR", str(reports))
    conn = connect(db)
    seed(conn)
    conn.close()
    return {"db": db, "reports": reports}


@pytest.fixture
def client(env):
    return TestClient(app)
