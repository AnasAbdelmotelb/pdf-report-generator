import json
from collections import Counter

import pytest

from app.db import connect
from app.report_data import get_report_data
from scripts.seed import RATINGS, SOURCE, seed

# Independent oracle: the same numbers computed in plain Python from the source file, not from SQL.
BOOKS = json.loads(SOURCE.read_text(encoding="utf-8"))


@pytest.fixture
def report(tmp_path):
    conn = connect(tmp_path / "test.db")
    seed(conn)
    yield get_report_data(conn)
    conn.close()


def test_has_exactly_the_four_sections(report):
    assert set(report) == {"total_books", "average_price", "top_5_most_expensive", "books_per_rating"}


def test_totals_match_the_source_data(report):
    assert report["total_books"] == len(BOOKS) == 60
    assert report["average_price"] == round(sum(b["price_gbp"] for b in BOOKS) / len(BOOKS), 2)


def test_top_5_is_the_five_highest_prices_in_order(report):
    expected = sorted(BOOKS, key=lambda b: (-b["price_gbp"], b["title"]))[:5]
    assert [row["title"] for row in report["top_5_most_expensive"]] == [b["title"] for b in expected]
    prices = [row["price"] for row in report["top_5_most_expensive"]]
    assert prices == sorted(prices, reverse=True)


def test_rating_breakdown_matches_and_adds_up(report):
    expected = Counter(RATINGS[b["rating_text"]] for b in BOOKS)
    assert {row["rating"]: row["books"] for row in report["books_per_rating"]} == dict(expected)
    assert sum(row["books"] for row in report["books_per_rating"]) == report["total_books"]


def test_report_is_valid_json(report):
    assert json.loads(json.dumps(report)) == report
