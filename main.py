import requests
import sqlite3
import pandas as pd
import argparse

API_KEY = "b26f9938c4a245d4b791bc91951588c8"

# -----------------------------
# DATABASE SETUP
# -----------------------------
conn = sqlite3.connect("news.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS news(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    title TEXT UNIQUE,
    published_at TEXT,
    url TEXT
)
""")

conn.commit()

# -----------------------------
# FETCH NEWS
# -----------------------------
def fetch_news(keyword="technology"):

    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={keyword}&"
        f"sortBy=publishedAt&"
        f"language=en&"
        f"apiKey={API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if data.get("status") != "ok":
        print("Error:", data)
        return

    for article in data["articles"]:

        source = article["source"]["name"]
        title = article["title"]
        date = article["publishedAt"]
        news_url = article["url"]

        cursor.execute("""
        INSERT OR IGNORE INTO news
        (source,title,published_at,url)
        VALUES (?,?,?,?)
        """,
        (source, title, date, news_url))

    conn.commit()
    print("News fetched successfully.")


# -----------------------------
# SHOW NEWS
# -----------------------------
def show_news(keyword=None, source=None):

    query = "SELECT source,title,published_at FROM news WHERE 1=1"
    params = []

    if keyword:
        query += " AND title LIKE ?"
        params.append(f"%{keyword}%")

    if source:
        query += " AND source LIKE ?"
        params.append(f"%{source}%")

    cursor.execute(query, params)

    rows = cursor.fetchall()

    if not rows:
        print("No news found.")
        return

    for row in rows:
        print("\n-------------------")
        print("Source :", row[0])
        print("Title  :", row[1])
        print("Date   :", row[2])


# -----------------------------
# EXPORT CSV
# -----------------------------
def export_csv():

    df = pd.read_sql_query(
        "SELECT * FROM news",
        conn
    )

    df.to_csv("news.csv", index=False)

    print("Exported to news.csv")


# -----------------------------
# EXPORT EXCEL
# -----------------------------
def export_excel():

    df = pd.read_sql_query(
        "SELECT * FROM news",
        conn
    )

    df.to_excel(
        "news.xlsx",
        index=False
    )

    print("Exported to news.xlsx")


# -----------------------------
# CLI
# -----------------------------
parser = argparse.ArgumentParser()

parser.add_argument(
    "--fetch",
    help="Fetch news by keyword"
)

parser.add_argument(
    "--keyword",
    help="Search stored news"
)

parser.add_argument(
    "--source",
    help="Filter by source"
)

parser.add_argument(
    "--csv",
    action="store_true"
)

parser.add_argument(
    "--excel",
    action="store_true"
)

args = parser.parse_args()

if args.fetch:
    fetch_news(args.fetch)

elif args.keyword or args.source:
    show_news(args.keyword, args.source)

elif args.csv:
    export_csv()

elif args.excel:
    export_excel()

else:
    print("""
Examples:

python main.py --fetch AI

python main.py --keyword AI

python main.py --source BBC

python main.py --csv

python main.py --excel
""")

conn.close()