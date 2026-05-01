#!/usr/bin/env python3
"""Persistent daily news watcher for the daily-news-watcher skill.

Provides a small CLI for managing a SQLite-backed list of news sources,
fetching recent articles from RSS/Atom feeds (with an optional Playwright
fallback), deduplicating them, and writing a Markdown report per run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_KNOWN_SOURCES = SKILL_DIR / "references" / "known-sources.csv"
DEFAULT_STATE = Path(
    os.environ.get(
        "DAILY_NEWS_WATCHER_STATE",
        str(Path.home() / ".codex" / "state" / "daily-news-watcher"),
    )
)

USER_AGENT = (
    "daily-news-watcher/0.1 (+https://github.com/Prompthon-IO/agentic-lab)"
)
REQUEST_TIMEOUT_SECONDS = 15
PER_SOURCE_ARTICLE_CAP = 25
SUMMARY_TARGET_CHARS = 280
TRACKING_PARAM_PREFIXES = ("utm_",)
TRACKING_PARAM_NAMES = {"gclid", "fbclid", "mc_cid", "mc_eid", "ref", "ref_src"}


# ---------------------------------------------------------------------------
# Time + path helpers
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def ensure_state_dirs(state_dir: Path) -> dict[str, Path]:
    paths = {
        "root": state_dir,
        "reports": state_dir / "reports" / "daily-news",
        "logs": state_dir / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    type TEXT NOT NULL,
    tags TEXT,
    created_at TEXT NOT NULL,
    last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    summary TEXT,
    hash TEXT NOT NULL,
    UNIQUE(url),
    UNIQUE(hash),
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL
);
"""


def open_db(state_dir: Path) -> sqlite3.Connection:
    state_dir.mkdir(parents=True, exist_ok=True)
    db_path = state_dir / "news.sqlite"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


# ---------------------------------------------------------------------------
# URL + text helpers
# ---------------------------------------------------------------------------


def canonical_url(raw: str) -> str:
    if not raw:
        return ""
    parsed = urllib.parse.urlsplit(raw.strip())
    scheme = parsed.scheme.lower() or "https"
    host = parsed.hostname or ""
    if parsed.port and not (
        (scheme == "http" and parsed.port == 80)
        or (scheme == "https" and parsed.port == 443)
    ):
        host = f"{host}:{parsed.port}"
    path = re.sub(r"/+$", "", parsed.path) or "/"
    pairs = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_PARAM_PREFIXES)
        and key.lower() not in TRACKING_PARAM_NAMES
    ]
    query = urllib.parse.urlencode(pairs)
    return urllib.parse.urlunsplit((scheme, host, path, query, ""))


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._chunks.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._chunks)).strip()


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    extractor = _TextExtractor()
    try:
        extractor.feed(unescape(value))
    except Exception:  # noqa: BLE001 - feed is best-effort.
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()
    return extractor.text()


def short_summary(text: str, target: int = SUMMARY_TARGET_CHARS) -> str:
    cleaned = strip_html(text)
    if len(cleaned) <= target:
        return cleaned
    window = cleaned[: target + 60]
    cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if cut >= target * 0.5:
        return window[: cut + 1].strip()
    return cleaned[:target].rstrip() + "..."


def content_hash(title: str, summary: str) -> str:
    normalized = re.sub(r"\s+", " ", f"{title.strip()}\n{summary.strip()}").lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_pubdate(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Fetching + parsing
# ---------------------------------------------------------------------------


def http_get(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def is_public_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    blocked_suffixes = (".local", ".internal", ".lan")
    blocked_exact = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if host in blocked_exact or host.endswith(blocked_suffixes):
        return False
    return True


def detect_feed_type(payload: bytes) -> str:
    head = payload.lstrip()[:512].lower()
    if b"<rss" in head or b"<rdf" in head:
        return "rss"
    if b"<feed" in head and b"atom" in head:
        return "atom"
    if b"<feed" in head:
        return "atom"
    return "webpage"


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse_feed(payload: bytes) -> list[dict[str, Any]]:
    """Parse RSS or Atom feed bytes into a list of article dicts."""

    if importlib.util.find_spec("feedparser") is not None:
        try:
            return _parse_feed_with_feedparser(payload)
        except Exception:  # noqa: BLE001 - fall back to stdlib parser.
            pass

    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return []

    items: list[dict[str, Any]] = []
    tag = _strip_ns(root.tag).lower()

    if tag == "rss":
        for item in root.iter():
            if _strip_ns(item.tag).lower() != "item":
                continue
            items.append(_extract_rss_item(item))
    elif tag == "feed":
        for entry in root.iter():
            if _strip_ns(entry.tag).lower() != "entry":
                continue
            items.append(_extract_atom_entry(entry))
    elif tag == "rdf":
        for item in root.iter():
            if _strip_ns(item.tag).lower() == "item":
                items.append(_extract_rss_item(item))

    return [item for item in items if item.get("title") and item.get("url")]


def _parse_feed_with_feedparser(payload: bytes) -> list[dict[str, Any]]:
    import feedparser  # type: ignore

    parsed = feedparser.parse(payload)
    items: list[dict[str, Any]] = []
    for entry in parsed.entries:
        link = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", "") or ""
        summary_html = getattr(entry, "summary", "") or getattr(entry, "description", "")
        published = (
            getattr(entry, "published", None)
            or getattr(entry, "updated", None)
            or getattr(entry, "pubDate", None)
        )
        items.append(
            {
                "title": strip_html(title),
                "url": link.strip(),
                "summary": short_summary(summary_html),
                "published_at": parse_pubdate(published),
            }
        )
    return [item for item in items if item.get("title") and item.get("url")]


def _extract_rss_item(node: ET.Element) -> dict[str, Any]:
    fields: dict[str, str] = {}
    for child in node:
        fields[_strip_ns(child.tag).lower()] = (child.text or "").strip()
    title = strip_html(fields.get("title", ""))
    link = fields.get("link", "")
    description = fields.get("description") or fields.get("encoded") or ""
    return {
        "title": title,
        "url": link,
        "summary": short_summary(description),
        "published_at": parse_pubdate(fields.get("pubdate") or fields.get("date")),
    }


def _extract_atom_entry(node: ET.Element) -> dict[str, Any]:
    title = ""
    summary = ""
    published = ""
    link = ""
    for child in node:
        local = _strip_ns(child.tag).lower()
        if local == "title":
            title = strip_html(child.text or "")
        elif local in {"summary", "content"} and not summary:
            summary = child.text or ""
        elif local in {"published", "updated"} and not published:
            published = child.text or ""
        elif local == "link":
            href = child.attrib.get("href")
            rel = child.attrib.get("rel", "alternate")
            if href and rel == "alternate" and not link:
                link = href
    return {
        "title": title,
        "url": link.strip(),
        "summary": short_summary(summary),
        "published_at": parse_pubdate(published),
    }


def parse_webpage(payload: bytes, source_url: str) -> list[dict[str, Any]]:
    """Best-effort: treat a non-feed page as a single article entry."""

    text = payload.decode("utf-8", errors="replace")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    title = strip_html(title_match.group(1)) if title_match else source_url

    desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        text,
        re.IGNORECASE,
    ) or re.search(
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        text,
        re.IGNORECASE,
    )
    summary = strip_html(desc_match.group(1)) if desc_match else ""
    if not summary:
        summary = short_summary(text)

    return [
        {
            "title": title,
            "url": source_url,
            "summary": summary,
            "published_at": None,
        }
    ]


def fetch_with_playwright(url: str) -> bytes | None:
    """Optional Playwright fallback. Returns None if Playwright is unavailable."""

    if importlib.util.find_spec("playwright") is None:
        return None
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=REQUEST_TIMEOUT_SECONDS * 1000)
            content = page.content()
            browser.close()
            return content.encode("utf-8")
    except Exception:  # noqa: BLE001 - best-effort fallback.
        return None


def fetch_source(source: sqlite3.Row, *, use_playwright: bool) -> tuple[list[dict[str, Any]], str | None]:
    url = source["url"]
    if not is_public_http_url(url):
        return [], "url is not a public http(s) URL"
    declared_type = (source["type"] or "").lower()

    try:
        payload = http_get(url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        if use_playwright:
            fallback = fetch_with_playwright(url)
            if fallback is not None:
                return parse_webpage(fallback, url), None
        return [], f"http error: {exc}"

    feed_type = declared_type if declared_type in {"rss", "atom"} else detect_feed_type(payload)
    if feed_type in {"rss", "atom"}:
        articles = parse_feed(payload)
        if articles:
            return articles[:PER_SOURCE_ARTICLE_CAP], None

    if use_playwright:
        rendered = fetch_with_playwright(url)
        if rendered is not None:
            return parse_webpage(rendered, url)[:PER_SOURCE_ARTICLE_CAP], None
    return parse_webpage(payload, url)[:PER_SOURCE_ARTICLE_CAP], None


# ---------------------------------------------------------------------------
# Source resolution
# ---------------------------------------------------------------------------


def load_known_sources(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def resolve_source(
    name: str,
    explicit_url: str | None,
    explicit_tags: str | None,
    known: Iterable[dict[str, str]],
) -> dict[str, str]:
    name_clean = name.strip()
    if explicit_url:
        return {
            "name": name_clean,
            "url": explicit_url.strip(),
            "type": "rss" if explicit_url.lower().endswith((".xml", ".rss", ".atom")) else "webpage",
            "tags": (explicit_tags or "").strip(),
        }

    lowered = name_clean.lower()
    for row in known:
        if row.get("name", "").strip().lower() == lowered:
            tags = (explicit_tags or row.get("tags") or "").strip()
            return {
                "name": row["name"],
                "url": row["url"],
                "type": row.get("type", "rss"),
                "tags": tags,
            }
    raise ValueError(
        f"Could not resolve source '{name}'. Pass --url to register it explicitly."
    )


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def matches_topic(topic: str, article: dict[str, Any], source_tags: str) -> bool:
    if not topic:
        return True
    needle = topic.lower()
    haystack = " ".join(
        [
            article.get("title", "") or "",
            article.get("summary", "") or "",
            source_tags or "",
        ]
    ).lower()
    return needle in haystack


def in_time_window(article: dict[str, Any], hours: int | None, now: datetime) -> bool:
    if not hours:
        return True
    cutoff = now - timedelta(hours=hours)
    candidate = article.get("published_at") or article.get("fetched_at")
    if not candidate:
        return True
    try:
        ts = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts >= cutoff


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def command_add_source(args: argparse.Namespace) -> int:
    known = load_known_sources(args.known_sources)
    try:
        resolved = resolve_source(args.name, args.url, args.tags, known)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not is_public_http_url(resolved["url"]):
        print(f"Refusing non-public URL: {resolved['url']}", file=sys.stderr)
        return 2

    try:
        http_get(resolved["url"], timeout=REQUEST_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - reachable check is informational.
        print(f"warning: source not reachable yet ({exc})", file=sys.stderr)

    state_dir = args.state_dir
    with open_db(state_dir) as db:
        existing = db.execute(
            "SELECT id FROM sources WHERE lower(name) = lower(?)",
            (resolved["name"],),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE sources SET url = ?, type = ?, tags = ? WHERE id = ?",
                (resolved["url"], resolved["type"], resolved["tags"], existing["id"]),
            )
            print(f"updated source id={existing['id']} name={resolved['name']}")
        else:
            cursor = db.execute(
                "INSERT INTO sources(name, url, type, tags, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    resolved["name"],
                    resolved["url"],
                    resolved["type"],
                    resolved["tags"],
                    utc_now_iso(),
                ),
            )
            print(f"added source id={cursor.lastrowid} name={resolved['name']}")
        db.commit()
    return 0


def command_list_sources(args: argparse.Namespace) -> int:
    with open_db(args.state_dir) as db:
        rows = db.execute(
            "SELECT id, name, url, type, tags, last_checked_at FROM sources ORDER BY name COLLATE NOCASE"
        ).fetchall()
    if not rows:
        print("no sources registered. use add-source to add one.")
        return 0
    for row in rows:
        last = row["last_checked_at"] or "never"
        tags = row["tags"] or ""
        print(f"[{row['id']}] {row['name']} ({row['type']}) tags={tags} last_checked={last} url={row['url']}")
    return 0


def command_remove_source(args: argparse.Namespace) -> int:
    with open_db(args.state_dir) as db:
        cursor = db.execute("DELETE FROM sources WHERE id = ?", (args.id,))
        db.commit()
    if cursor.rowcount == 0:
        print(f"no source with id={args.id}", file=sys.stderr)
        return 1
    print(f"removed source id={args.id}")
    return 0


def command_fetch(args: argparse.Namespace) -> int:
    state_dir = args.state_dir
    paths = ensure_state_dirs(state_dir)
    rid = run_id()
    started = utc_now_iso()
    now = utc_now()

    with open_db(state_dir) as db:
        run_cursor = db.execute(
            "INSERT INTO runs(topic, started_at, status) VALUES (?, ?, ?)",
            (args.topic, started, "running"),
        )
        run_pk = run_cursor.lastrowid
        db.commit()

        sources = db.execute(
            "SELECT id, name, url, type, tags, last_checked_at FROM sources ORDER BY id"
        ).fetchall()

        if not sources:
            db.execute(
                "UPDATE runs SET finished_at = ?, status = ? WHERE id = ?",
                (utc_now_iso(), "no_sources", run_pk),
            )
            db.commit()
            print("no sources registered. use add-source first.")
            return 1

        per_source: list[dict[str, Any]] = []
        included_articles: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        seen_hashes: set[str] = set()

        for source in sources:
            entry: dict[str, Any] = {
                "source_id": source["id"],
                "source_name": source["name"],
                "fetched": 0,
                "new": 0,
                "kept": 0,
                "skipped_duplicate": 0,
                "skipped_filter": 0,
                "error": None,
            }
            articles, error = fetch_source(source, use_playwright=args.use_playwright)
            if error:
                entry["error"] = error
                per_source.append(entry)
                continue

            entry["fetched"] = len(articles)
            for article in articles:
                title = (article.get("title") or "").strip()
                url = (article.get("url") or "").strip()
                if not title or not url:
                    continue
                canon = canonical_url(url)
                summary = article.get("summary") or ""
                digest = content_hash(title, summary)
                fetched_iso = utc_now_iso()
                article_record = {
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "source_tags": source["tags"] or "",
                    "title": title,
                    "url": canon,
                    "summary": summary,
                    "published_at": article.get("published_at"),
                    "fetched_at": fetched_iso,
                    "hash": digest,
                }

                if canon in seen_urls or digest in seen_hashes:
                    entry["skipped_duplicate"] += 1
                    continue

                already = db.execute(
                    "SELECT 1 FROM articles WHERE url = ? OR hash = ? LIMIT 1",
                    (canon, digest),
                ).fetchone()
                if already:
                    entry["skipped_duplicate"] += 1
                    continue

                if not in_time_window(article_record, args.hours, now):
                    entry["skipped_filter"] += 1
                    continue
                if not matches_topic(args.topic or "", article_record, source["tags"] or ""):
                    entry["skipped_filter"] += 1
                    continue

                seen_urls.add(canon)
                seen_hashes.add(digest)
                db.execute(
                    "INSERT INTO articles(source_id, title, url, published_at, fetched_at, summary, hash)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        source["id"],
                        title,
                        canon,
                        article_record["published_at"],
                        fetched_iso,
                        summary,
                        digest,
                    ),
                )
                entry["new"] += 1
                entry["kept"] += 1
                included_articles.append(article_record)

            db.execute(
                "UPDATE sources SET last_checked_at = ? WHERE id = ?",
                (utc_now_iso(), source["id"]),
            )
            per_source.append(entry)
            db.commit()

        finished = utc_now_iso()
        status = "ok"
        if all(entry.get("error") for entry in per_source):
            status = "all_sources_failed"
        elif any(entry.get("error") for entry in per_source):
            status = "partial"
        db.execute(
            "UPDATE runs SET finished_at = ?, status = ? WHERE id = ?",
            (finished, status, run_pk),
        )
        db.commit()

    report_path = write_report(
        rid=rid,
        report_dir=paths["reports"],
        topic=args.topic,
        hours=args.hours,
        per_source=per_source,
        articles=included_articles,
        started=started,
        finished=finished,
        status=status,
    )
    log_path = paths["logs"] / f"{rid}-fetch.json"
    log_path.write_text(
        json.dumps(
            {
                "run_id": rid,
                "started_at": started,
                "finished_at": finished,
                "status": status,
                "topic": args.topic,
                "hours": args.hours,
                "per_source": per_source,
                "articles": included_articles,
                "report_path": str(report_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"report={report_path}")
    print(f"log={log_path}")
    print(f"status={status}")
    print(f"articles_included={len(included_articles)}")
    print(f"sources_with_errors={sum(1 for entry in per_source if entry.get('error'))}")
    return 0


def command_runs(args: argparse.Namespace) -> int:
    with open_db(args.state_dir) as db:
        rows = db.execute(
            "SELECT id, topic, started_at, finished_at, status FROM runs ORDER BY id DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
    if not rows:
        print("no runs recorded yet.")
        return 0
    for row in rows:
        topic = row["topic"] or "(no topic)"
        finished = row["finished_at"] or "in-progress"
        print(f"[{row['id']}] topic={topic} status={row['status']} started={row['started_at']} finished={finished}")
    return 0


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_report(
    *,
    rid: str,
    report_dir: Path,
    topic: str | None,
    hours: int | None,
    per_source: list[dict[str, Any]],
    articles: list[dict[str, Any]],
    started: str,
    finished: str,
    status: str,
) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    topic_slug = re.sub(r"[^a-z0-9]+", "-", (topic or "all").lower()).strip("-") or "all"
    report_path = report_dir / f"{today}-{topic_slug}.md"

    lines = [
        f"# Daily News - {today} - {topic or 'All Topics'}",
        "",
        f"- Run: `{rid}`",
        f"- Started: `{started}`",
        f"- Finished: `{finished}`",
        f"- Status: `{status}`",
        f"- Window: last {hours} hours" if hours else "- Window: all available",
        f"- Topic filter: `{topic}`" if topic else "- Topic filter: none",
        f"- Articles included: {len(articles)}",
        "",
        "## Sources Checked",
        "",
        "| Source | Fetched | New | Kept | Dup skipped | Filter skipped | Error |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for entry in per_source:
        error = (entry.get("error") or "").replace("|", "\\|")
        lines.append(
            f"| {entry['source_name']} | {entry['fetched']} | {entry['new']} | {entry['kept']} |"
            f" {entry['skipped_duplicate']} | {entry['skipped_filter']} | {error} |"
        )

    lines.extend(["", "## Articles", ""])
    if articles:
        articles_sorted = sorted(
            articles,
            key=lambda a: (a.get("published_at") or a.get("fetched_at") or ""),
            reverse=True,
        )
        for article in articles_sorted:
            published = article.get("published_at") or article.get("fetched_at") or ""
            title = article["title"].replace("|", "\\|")
            lines.extend(
                [
                    f"### {title}",
                    "",
                    f"- Source: {article['source_name']}",
                    f"- Published: `{published}`",
                    f"- Link: <{article['url']}>",
                    "",
                    article.get("summary") or "_(no summary extracted)_",
                    "",
                ]
            )
    else:
        lines.append("_No articles matched the topic and time window._")
        lines.append("")

    errors = [entry for entry in per_source if entry.get("error")]
    if errors:
        lines.extend(["## Skipped / Errors", ""])
        for entry in errors:
            lines.append(f"- {entry['source_name']}: {entry['error']}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persistent daily news watcher (SQLite + Markdown reports).",
    )
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add-source", help="Register a news source.")
    add.add_argument("--name", required=True)
    add.add_argument("--url", default=None, help="Explicit URL. Required for unknown publications.")
    add.add_argument("--tags", default=None, help="Semicolon-separated tags, e.g. 'AI;tech'.")
    add.add_argument("--known-sources", type=Path, default=DEFAULT_KNOWN_SOURCES)
    add.set_defaults(func=command_add_source)

    listing = subparsers.add_parser("list-sources", help="List registered sources.")
    listing.set_defaults(func=command_list_sources)

    remove = subparsers.add_parser("remove-source", help="Remove a source by id.")
    remove.add_argument("--id", type=int, required=True)
    remove.set_defaults(func=command_remove_source)

    fetch = subparsers.add_parser("fetch", help="Fetch sources, dedupe, and write a Markdown report.")
    fetch.add_argument("--hours", type=int, default=24)
    fetch.add_argument("--topic", default=None)
    fetch.add_argument("--use-playwright", action="store_true")
    fetch.set_defaults(func=command_fetch)

    runs = subparsers.add_parser("runs", help="Show recent fetch runs.")
    runs.add_argument("--limit", type=int, default=10)
    runs.set_defaults(func=command_runs)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
