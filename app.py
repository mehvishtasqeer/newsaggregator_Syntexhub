
import os
import sqlite3
from io import BytesIO

import pandas as pd
import requests
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-for-local-demo"
)

# Database configuration
DB_NAME = r"C:\Users\mehvi\OneDrive\Desktop\news aggregator\news.db"

# NewsAPI key
API_KEY = os.getenv("NEWSAPI_KEY")


# Connect to database
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                title TEXT UNIQUE,
                published_at TEXT,
                url TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


initialize_database()
# Create news table if it does not exist
def create_table():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                title TEXT UNIQUE,
                published_at TEXT,
                url TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


# Fetch news from NewsAPI and save it
def fetch_news(keyword):
    if not API_KEY:
        raise RuntimeError(
            "NEWSAPI_KEY is not set. Set it in PowerShell before starting the app."
        )

    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": keyword,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": API_KEY,
        },
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    if data.get("status") != "ok":
        raise RuntimeError(
            data.get("message", "NewsAPI returned an error.")
        )

    conn = get_connection()

    try:
        for article in data.get("articles", []):
            source = (article.get("source") or {}).get("name") or "Unknown"
            title = article.get("title")
            published_at = article.get("publishedAt")
            article_url = article.get("url")

            if title:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO news
                    (source, title, published_at, url)
                    VALUES (?, ?, ?, ?)
                    """,
                    (source, title, published_at, article_url),
                )

        conn.commit()

    finally:
        conn.close()


# Search and filter stored articles
def get_articles(keyword="", source=""):
    conn = get_connection()

    try:
        query = """
            SELECT source, title, published_at, url
            FROM news
            WHERE 1=1
        """

        params = []

        if keyword:
            query += " AND title LIKE ?"
            params.append(f"%{keyword}%")

        if source:
            query += " AND source LIKE ?"
            params.append(f"%{source}%")

        query += " ORDER BY published_at DESC"

        return conn.execute(query, params).fetchall()

    finally:
        conn.close()


# Home page
@app.route("/", methods=["GET"])
def index():
    keyword = request.args.get("keyword", "").strip()
    source = request.args.get("source", "").strip()

    articles = get_articles(keyword, source)

    conn = get_connection()

    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM news"
        ).fetchone()[0]

        sources = conn.execute(
            "SELECT COUNT(DISTINCT source) FROM news"
        ).fetchone()[0]

    finally:
        conn.close()

    return render_template(
        "index.html",
        articles=articles,
        keyword=keyword,
        source=source,
        total=total,
        sources=sources,
    )


# Fetch news route
@app.route("/fetch", methods=["POST"])
def fetch():
    keyword = request.form.get("keyword", "").strip()

    if not keyword:
        flash("Enter a keyword before fetching news.", "error")
        return redirect(url_for("index"))

    try:
        fetch_news(keyword)
        flash(
            f'News for "{keyword}" fetched and saved successfully.',
            "success"
        )

    except requests.RequestException as exc:
        flash(f"Could not contact NewsAPI: {exc}", "error")

    except Exception as exc:
        flash(str(exc), "error")

    return redirect(url_for("index", keyword=keyword))


# Export articles to CSV
@app.route("/export/csv")
def export_csv():
    keyword = request.args.get("keyword", "").strip()
    source = request.args.get("source", "").strip()

    articles = get_articles(keyword, source)
    df = pd.DataFrame([dict(row) for row in articles])

    if df.empty:
        flash("There are no matching articles to export.", "error")
        return redirect(
            url_for("index", keyword=keyword, source=source)
        )

    output = BytesIO()

    df.to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )

    output.seek(0)

    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="news_export.csv",
    )


# Export articles to Excel
@app.route("/export/excel")
def export_excel():
    keyword = request.args.get("keyword", "").strip()
    source = request.args.get("source", "").strip()

    articles = get_articles(keyword, source)
    df = pd.DataFrame([dict(row) for row in articles])

    if df.empty:
        flash("There are no matching articles to export.", "error")
        return redirect(
            url_for("index", keyword=keyword, source=source)
        )

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="News"
        )

    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="news_export.xlsx",
    )


# Run Flask application
if __name__ == "__main__":
    create_table()
    app.run(debug=True)

