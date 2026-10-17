import sqlite3

# The four aggregation queries behind the report (pasted into the README as-is).
TOTAL_BOOKS = "SELECT COUNT(*) AS total_books FROM books"

AVERAGE_PRICE = "SELECT ROUND(AVG(price), 2) AS average_price FROM books"

TOP_5_MOST_EXPENSIVE = """
SELECT title, price, rating
FROM books
ORDER BY price DESC, title
LIMIT 5
"""

BOOKS_PER_RATING = """
SELECT rating, COUNT(*) AS books
FROM books
GROUP BY rating
ORDER BY rating DESC
"""


def get_report_data(conn: sqlite3.Connection) -> dict:
    """Turns the books table into the report's numbers: two totals, a top 5 and a breakdown."""
    return {
        "total_books": conn.execute(TOTAL_BOOKS).fetchone()["total_books"],
        "average_price": conn.execute(AVERAGE_PRICE).fetchone()["average_price"],
        "top_5_most_expensive": [dict(row) for row in conn.execute(TOP_5_MOST_EXPENSIVE)],
        "books_per_rating": [dict(row) for row in conn.execute(BOOKS_PER_RATING)],
    }
