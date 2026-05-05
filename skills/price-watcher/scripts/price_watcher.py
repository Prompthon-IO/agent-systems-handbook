#!/usr/bin/env python3
"""Local helper for the price-watcher Codex skill.

This script manages SQLite state and Markdown reporting. It intentionally does
not bypass retailer access controls or perform checkout actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sqlite3
from pathlib import Path
from typing import Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query TEXT NOT NULL,
  normalized_name TEXT,
  target_price REAL,
  created_at TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  site TEXT NOT NULL,
  url TEXT NOT NULL,
  last_checked_at TEXT,
  UNIQUE(item_id, url)
);

CREATE TABLE IF NOT EXISTS price_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  price REAL NOT NULL,
  currency TEXT NOT NULL,
  checked_at TEXT NOT NULL
);
"""


PRICE_RE = re.compile(
    r"(?:below|under|less than|drops? below|at or below|<=|<)\s*"
    r"(?P<symbol>US\$|CA\$|[$£€])?\s*(?P<amount>\d[\d,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def infer_currency(symbol: str | None) -> str:
    return {
        "US$": "USD",
        "CA$": "CAD",
        "$": "USD",
        "£": "GBP",
        "€": "EUR",
    }.get(symbol or "$", "USD")


def parse_watch_request(text: str) -> tuple[str, float | None, str]:
    match = PRICE_RE.search(text)
    target = None
    currency = "USD"
    query = text.strip()
    if match:
        target = float(match.group("amount").replace(",", ""))
        currency = infer_currency(match.group("symbol"))
        query = text[: match.start()].strip()
    query = re.sub(r"^(watch|track|monitor)\s+", "", query, flags=re.IGNORECASE).strip()
    query = re.sub(r"\s+and\s+(notify|tell|alert)\s+me\s+if\s+it\s*$", "", query, flags=re.IGNORECASE).strip()
    return query or text.strip(), target, currency


def normalize_name(query: str) -> str:
    cleaned = re.sub(r"\s+", " ", query).strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


def add_item(conn: sqlite3.Connection, request: str) -> sqlite3.Row:
    query, target, _currency = parse_watch_request(request)
    cur = conn.execute(
        """
        INSERT INTO items(query, normalized_name, target_price, created_at, active)
        VALUES (?, ?, ?, ?, 1)
        """,
        (query, normalize_name(query), target, utc_now()),
    )
    conn.commit()
    return conn.execute("SELECT * FROM items WHERE id = ?", (cur.lastrowid,)).fetchone()


def add_source(conn: sqlite3.Connection, item_id: int, site: str, url: str) -> sqlite3.Row:
    conn.execute(
        """
        INSERT OR IGNORE INTO sources(item_id, site, url)
        VALUES (?, ?, ?)
        """,
        (item_id, site, url),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM sources WHERE item_id = ? AND url = ?",
        (item_id, url),
    ).fetchone()


def record_price(
    conn: sqlite3.Connection,
    item_id: int,
    source_id: int,
    price: float,
    currency: str,
    checked_at: str | None = None,
) -> sqlite3.Row:
    checked_at = checked_at or utc_now()
    cur = conn.execute(
        """
        INSERT INTO price_checks(item_id, source_id, price, currency, checked_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (item_id, source_id, price, currency.upper(), checked_at),
    )
    conn.execute("UPDATE sources SET last_checked_at = ? WHERE id = ?", (checked_at, source_id))
    conn.commit()
    return conn.execute("SELECT * FROM price_checks WHERE id = ?", (cur.lastrowid,)).fetchone()


def latest_prices(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    return conn.execute(
        """
        WITH ranked AS (
          SELECT
            pc.*,
            s.site,
            s.url,
            i.query,
            i.normalized_name,
            i.target_price,
            ROW_NUMBER() OVER (
              PARTITION BY pc.source_id
              ORDER BY pc.checked_at DESC, pc.id DESC
            ) AS rn
          FROM price_checks pc
          JOIN sources s ON s.id = pc.source_id
          JOIN items i ON i.id = pc.item_id
          WHERE i.active = 1
        )
        SELECT * FROM ranked
        WHERE rn = 1
        ORDER BY price ASC, checked_at DESC
        """
    ).fetchall()


def previous_price(conn: sqlite3.Connection, source_id: int, latest_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM price_checks
        WHERE source_id = ? AND id <> ?
        ORDER BY checked_at DESC, id DESC
        LIMIT 1
        """,
        (source_id, latest_id),
    ).fetchone()


def money(price: float, currency: str) -> str:
    return f"{currency} {price:,.2f}"


def write_report(conn: sqlite3.Connection, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{dt.date.today().isoformat()}.md"
    rows = list(latest_prices(conn))

    lines = [
        f"# Price Watch Report - {dt.date.today().isoformat()}",
        "",
        "Sorted by lowest currently observed price.",
        "",
    ]

    if not rows:
        lines.extend(["No price observations recorded yet.", ""])
    current_item = None
    for row in rows:
        if row["item_id"] != current_item:
            current_item = row["item_id"]
            target = row["target_price"]
            target_text = f"target {target:,.2f}" if target is not None else "no target price"
            lines.extend(
                [
                    f"## {row['normalized_name'] or row['query']}",
                    "",
                    f"- Query: {row['query']}",
                    f"- Threshold: {target_text}",
                    "",
                    "| Source | Observed price | Target status | Change | Checked |",
                    "| --- | ---: | --- | ---: | --- |",
                ]
            )
        prev = previous_price(conn, int(row["source_id"]), int(row["id"]))
        change = ""
        if prev:
            delta = float(row["price"]) - float(prev["price"])
            change = f"{delta:+,.2f}"
        target_status = "No target"
        if row["target_price"] is not None:
            target_status = "Met" if float(row["price"]) <= float(row["target_price"]) else "Above target"
        source = f"[{row['site']}]({row['url']})"
        lines.append(
            f"| {source} | {money(float(row['price']), row['currency'])} | "
            f"{target_status} | {change or 'n/a'} | {row['checked_at']} |"
        )
    lines.append("")
    lines.append("Failed or skipped source notes: add source-specific notes here when a check could not store a price.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage price-watcher SQLite state and reports.")
    parser.add_argument("--db", default="price-watcher.sqlite3", help="SQLite database path.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create SQLite tables.")

    add = sub.add_parser("add", help="Add a natural-language watched item.")
    add.add_argument("request")

    sources = sub.add_parser("sources", help="Manage source URLs.")
    sources_sub = sources.add_subparsers(dest="sources_command", required=True)
    sources_add = sources_sub.add_parser("add", help="Add a source URL for an item.")
    sources_add.add_argument("--item-id", type=int, required=True)
    sources_add.add_argument("--site", required=True)
    sources_add.add_argument("--url", required=True)

    record = sub.add_parser("record", help="Record an observed price.")
    record.add_argument("--item-id", type=int, required=True)
    record.add_argument("--source-id", type=int, required=True)
    record.add_argument("--price", type=float, required=True)
    record.add_argument("--currency", default="USD")

    report = sub.add_parser("report", help="Write a Markdown report.")
    report.add_argument("--report-dir", default="price-reports")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_path = Path(args.db)
    with connect(db_path) as conn:
        init_db(conn)
        if args.command == "init":
            print(f"Initialized {db_path}")
        elif args.command == "add":
            row = add_item(conn, args.request)
            print(f"Added item {row['id']}: {row['query']} target={row['target_price']}")
        elif args.command == "sources" and args.sources_command == "add":
            row = add_source(conn, args.item_id, args.site, args.url)
            print(f"Source {row['id']}: {row['site']} {row['url']}")
        elif args.command == "record":
            row = record_price(conn, args.item_id, args.source_id, args.price, args.currency)
            print(f"Recorded check {row['id']}: {money(float(row['price']), row['currency'])}")
        elif args.command == "report":
            path = write_report(conn, Path(args.report_dir))
            print(path)


if __name__ == "__main__":
    main()
