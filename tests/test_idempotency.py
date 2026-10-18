import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest

from app.db import connect
from app.reports import generate_report


def pdf_files(env):
    return sorted(p.name for p in env["reports"].glob("*.pdf")) if env["reports"].exists() else []


def test_two_posts_on_the_same_day_return_the_same_report(client, env):
    first = client.post("/reports")
    second = client.post("/reports")
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json() == second.json() == {"id": 1, "file": "/reports/1/file"}
    assert pdf_files(env) == ["1.pdf"]


def test_two_simultaneous_posts_still_make_one_report(client, env):
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post("/reports"), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 201]
    assert {r.json()["id"] for r in responses} == {1}
    assert pdf_files(env) == ["1.pdf"]


def test_force_true_makes_a_new_report(client, env):
    client.post("/reports")
    forced = client.post("/reports", json={"force": True})
    assert forced.status_code == 201 and forced.json()["id"] == 2
    again = client.post("/reports")  # a normal request still returns the day's first report
    assert again.status_code == 200 and again.json()["id"] == 1
    assert pdf_files(env) == ["1.pdf", "2.pdf"]


def test_force_false_and_empty_body_follow_the_daily_rule(client):
    client.post("/reports")
    assert client.post("/reports", json={"force": False}).status_code == 200
    assert client.post("/reports", json={}).status_code == 200


def test_unknown_fields_are_rejected(client):
    assert client.post("/reports", json={"forse": True}).status_code == 422


def test_a_new_day_gets_a_new_report(env):
    conn = connect(env["db"])
    today = datetime(2026, 10, 17, 23, 59).astimezone()
    first, created_first = generate_report(conn, env["reports"], now=today)
    second, created_second = generate_report(conn, env["reports"], now=today + timedelta(minutes=2))
    assert created_first and created_second
    assert second["id"] != first["id"]
    conn.close()


def test_the_database_itself_refuses_a_second_normal_report_for_a_day(env):
    conn = connect(env["db"])
    insert = "INSERT INTO reports (path, created_at, report_date, forced) VALUES ('x', 'now', '2026-10-17', ?)"
    conn.execute(insert, (0,))
    conn.execute(insert, (1,))  # forced reports are allowed alongside
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, (0,))
    conn.close()


def test_reports_made_before_stage_5_do_not_block_today(client, env):
    # A Stage 4 database: reports without report_date / forced columns.
    sqlite3.connect(env["db"]).executescript(
        "DROP TABLE reports; CREATE TABLE reports (id INTEGER PRIMARY KEY, path TEXT NOT NULL, created_at TEXT NOT NULL);"
        "INSERT INTO reports (path, created_at) VALUES ('reports/1.pdf', '2026-10-17T10:00:00+03:00');"
    ).close()
    response = client.post("/reports")
    assert response.status_code == 201 and response.json()["id"] == 2
