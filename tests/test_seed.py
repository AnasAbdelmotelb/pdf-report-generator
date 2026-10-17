import json

import pytest

from app.db import connect
from scripts.seed import SOURCE, seed, to_row


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


def test_seed_loads_all_60_books(conn):
    assert seed(conn) == 60


def test_seeding_twice_leaves_one_clean_copy(conn):
    seed(conn)
    assert seed(conn) == 60
    ids = [row[0] for row in conn.execute("SELECT id FROM books ORDER BY id")]
    assert ids == list(range(1, 61))  # ids restart, no duplicates


def test_fields_are_mapped_and_typed(conn):
    seed(conn)
    first = conn.execute("SELECT title, price, rating, url FROM books WHERE id = 1").fetchone()
    assert dict(first) == {
        "title": "A Light in the Attic",
        "price": 51.77,
        "rating": 3,
        "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    }
    ratings = {row[0] for row in conn.execute("SELECT DISTINCT rating FROM books")}
    assert ratings == {1, 2, 3, 4, 5}


def test_unknown_rating_word_is_rejected():
    with pytest.raises(KeyError):
        to_row({"title": "x", "price_gbp": 1.0, "rating_text": "Six", "product_url": "u"})


def test_failed_seed_keeps_the_existing_rows(conn, tmp_path):
    seed(conn)
    bad = tmp_path / "bad.json"
    books = json.loads(SOURCE.read_text())
    books[5]["rating_text"] = "Zero"
    bad.write_text(json.dumps(books))
    with pytest.raises(KeyError):
        seed(conn, bad)
    assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 60
