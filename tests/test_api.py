import sqlite3

import pytest

import app.reports


def report_rows(env):
    with sqlite3.connect(env["db"]) as conn:
        return conn.execute("SELECT id, path FROM reports").fetchall()


def test_post_generates_a_pdf_and_returns_201_with_a_link(client, env):
    response = client.post("/reports")
    assert response.status_code == 201
    body = response.json()
    assert body == {"id": 1, "file": "/reports/1/file"}
    assert len(response.content) < 100  # a few bytes of JSON, never the file
    assert (env["reports"] / "1.pdf").read_bytes().startswith(b"%PDF-")
    assert report_rows(env) == [(1, str(env["reports"] / "1.pdf"))]


def test_get_report_returns_the_record_with_its_link(client):
    created = client.post("/reports").json()
    response = client.get(f"/reports/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"] and body["file"] == "/reports/1/file"
    assert body["created_at"][:4].isdigit() and body["path"].endswith("1.pdf")


def test_unknown_report_is_404(client):
    assert client.get("/reports/999").status_code == 404
    assert client.get("/reports/999/file").status_code == 404


def test_file_endpoint_serves_the_stored_pdf(client, env):
    client.post("/reports")
    response = client.get("/reports/1/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == (env["reports"] / "1.pdf").read_bytes()
    assert 'filename="report-1.pdf"' in response.headers["content-disposition"]


def test_missing_file_on_disk_is_404_not_a_crash(client, env):
    client.post("/reports")
    (env["reports"] / "1.pdf").unlink()
    response = client.get("/reports/1/file")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report file is missing on disk"


def test_failed_render_leaves_no_row_and_no_file(client, env, monkeypatch):
    def broken_render(html, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"half a pdf")
        raise RuntimeError("browser crashed")

    monkeypatch.setattr(app.reports, "render_pdf", broken_render)
    with pytest.raises(RuntimeError):
        client.post("/reports")
    assert report_rows(env) == []
    assert not (env["reports"] / "1.pdf").exists()
