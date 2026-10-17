"""Fill report.db with the 60 books scraped in A9 (data/books.json).

Safe to run twice: it deletes all rows first, so the table always holds one clean copy.
Usage: python -m scripts.seed
"""
import json
from pathlib import Path

from app.db import ROOT, connect, transaction

SOURCE = ROOT / "data" / "books.json"
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def to_row(book: dict) -> tuple[str, float, int, str]:
    # A9 field names -> the brief's books table: price_gbp -> price, rating_text -> rating, product_url -> url
    return (book["title"], float(book["price_gbp"]), RATINGS[book["rating_text"]], book["product_url"])


def seed(conn, source: Path = SOURCE) -> int:
    rows = [to_row(book) for book in json.loads(source.read_text(encoding="utf-8"))]
    with transaction(conn):  # delete and insert succeed or fail together
        conn.execute("DELETE FROM books")
        conn.executemany("INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)", rows)
    return conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]


if __name__ == "__main__":
    conn = connect()
    print(f"Seeded {seed(conn)} books into {conn.execute('PRAGMA database_list').fetchone()['file']}")
