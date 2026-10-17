import re
from datetime import date

import pytest

from app.db import connect
from app.render import build_html, render_pdf
from app.report_data import get_all_books, get_report_data
from scripts.seed import seed

TODAY = date(2026, 10, 17)


@pytest.fixture
def data(tmp_path):
    conn = connect(tmp_path / "test.db")
    seed(conn)
    yield get_report_data(conn), get_all_books(conn)
    conn.close()


def page_count(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


def test_html_has_title_date_totals_and_all_books(data):
    report, books = data
    html = build_html(report, books, TODAY)
    assert "<h1>Bookstore report</h1>" in html and "17 October 2026" in html
    assert ">60<" in html and "£35.00" in html
    assert html.count("<tr>") == 1 + 5 + 1 + 5 + 1 + 60  # header + top 5, header + ratings, header + all books


def test_print_css_repeats_headers_and_keeps_rows_whole(data):
    html = build_html(*data, TODAY)
    assert "thead { display: table-header-group; }" in html
    assert "tr { break-inside: avoid; }" in html
    assert html.count("<thead>") == 3


def test_text_from_the_data_is_escaped():
    report = {"total_books": 1, "average_price": 1.0, "top_5_most_expensive": [], "books_per_rating": []}
    books = [{"id": 1, "title": "<script>alert(1)</script> & Co", "price": 1.0, "rating": 5}]
    html = build_html(report, books, TODAY)
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; Co" in html


def test_renders_a_real_pdf_of_at_least_two_pages(data, tmp_path):
    path = render_pdf(build_html(*data, TODAY), tmp_path / "reports" / "test.pdf")
    pdf = path.read_bytes()
    assert pdf.startswith(b"%PDF-")
    assert page_count(pdf) >= 2
