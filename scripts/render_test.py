"""Render the report to reports/test.pdf. Usage: python -m scripts.render_test"""
from datetime import date

from app.db import ROOT, connect
from app.render import build_html, render_pdf
from app.report_data import get_all_books, get_report_data

if __name__ == "__main__":
    conn = connect()
    html = build_html(get_report_data(conn), get_all_books(conn), date.today())
    print("Wrote", render_pdf(html, ROOT / "reports" / "test.pdf").relative_to(ROOT))
