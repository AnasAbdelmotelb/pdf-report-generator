from datetime import date
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

STYLE = """
@page { size: A4; margin: 16mm 14mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1c2b29; font-size: 10pt; }
h1 { margin: 0 0 2pt; font-size: 20pt; }
.date { margin: 0 0 14pt; color: #5b6b68; }
h2 { margin: 18pt 0 6pt; font-size: 13pt; }
.totals { display: flex; gap: 10pt; }
.total { flex: 1; padding: 10pt 12pt; border: 1px solid #d9e4e1; border-radius: 6pt; background: #f3f8f6; }
.total .value { font-size: 20pt; font-weight: 700; }
.total .label { color: #5b6b68; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 5pt 6pt; text-align: left; vertical-align: top; border-bottom: 1px solid #e3ece9; }
th { background: #e8f1ee; font-size: 9pt; }
td.num, th.num { text-align: right; white-space: nowrap; }
/* print-css:start (the page-break fix) */
thead { display: table-header-group; } /* repeat the header row on every page */
tr { break-inside: avoid; }            /* never slice a row across a page break */
h2 { break-after: avoid; }             /* keep a heading with its table */
/* print-css:end */
"""


def _stars(rating: int) -> str:
    return "★" * rating + "☆" * (5 - rating)


def build_html(report: dict, books: list[dict], today: date) -> str:
    """Pours the report numbers into an HTML page. All text from the data is escaped."""
    top5 = "".join(
        f"<tr><td>{i}</td><td>{escape(b['title'])}</td><td>{_stars(b['rating'])}</td>"
        f"<td class='num'>£{b['price']:.2f}</td></tr>"
        for i, b in enumerate(report["top_5_most_expensive"], 1)
    )
    ratings = "".join(
        f"<tr><td>{_stars(r['rating'])} ({r['rating']})</td><td class='num'>{r['books']}</td></tr>"
        for r in report["books_per_rating"]
    )
    all_books = "".join(
        f"<tr><td>{b['id']}</td><td>{escape(b['title'])}</td><td>{_stars(b['rating'])}</td>"
        f"<td class='num'>£{b['price']:.2f}</td></tr>"
        for b in books
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Bookstore report {today.isoformat()}</title>
<style>{STYLE}</style></head>
<body>
  <h1>Bookstore report</h1>
  <p class="date">{today.strftime("%d %B %Y")} · data scraped from books.toscrape.com</p>

  <div class="totals">
    <div class="total"><div class="value">{report["total_books"]}</div><div class="label">books</div></div>
    <div class="total"><div class="value">£{report["average_price"]:.2f}</div><div class="label">average price</div></div>
  </div>

  <h2>Top 5 most expensive books</h2>
  <table>
    <thead><tr><th>#</th><th>Title</th><th>Rating</th><th class="num">Price</th></tr></thead>
    <tbody>{top5}</tbody>
  </table>

  <h2>Books per star rating</h2>
  <table>
    <thead><tr><th>Rating</th><th class="num">Books</th></tr></thead>
    <tbody>{ratings}</tbody>
  </table>

  <h2>All books</h2>
  <table>
    <thead><tr><th>ID</th><th>Title</th><th>Rating</th><th class="num">Price</th></tr></thead>
    <tbody>{all_books}</tbody>
  </table>
</body></html>"""


def render_pdf(html: str, path: Path) -> Path:
    """Prints the HTML to an A4 PDF with headless Chromium."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(path=str(path), format="A4", print_background=True)
        finally:
            browser.close()
    return path
