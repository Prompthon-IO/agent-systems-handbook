#!/usr/bin/env python3
"""Local-first helper for the personal-knowledge-capture skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree


DEFAULT_STATE = Path(
    os.environ.get(
        "PERSONAL_KNOWLEDGE_CAPTURE_STATE",
        str(Path.home() / ".codex" / "state" / "personal-knowledge-capture"),
    )
)
SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf", ".docx"}
TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
MAX_CAPTURE_CHARS = 12000
MAX_NOTE_CHARS = 1200


@dataclass
class CaptureItem:
    source: str
    title: str
    status: str
    digest: str | None = None
    captured_at: str | None = None
    text: str = ""
    summary_path: str | None = None
    reason: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def expand_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def ensure_state_dirs(state_dir: Path) -> dict[str, Path]:
    paths = {
        "state": state_dir,
        "runs": state_dir / "runs",
        "notes": state_dir / "knowledge-notes",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def connect_db(state_dir: Path) -> sqlite3.Connection:
    ensure_state_dirs(state_dir)
    connection = sqlite3.connect(state_dir / "knowledge_capture.db")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS watch_paths (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          path TEXT NOT NULL UNIQUE,
          tags TEXT,
          created_at TEXT NOT NULL,
          last_scanned_at TEXT
        );

        CREATE TABLE IF NOT EXISTS documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          path_or_url TEXT NOT NULL UNIQUE,
          title TEXT,
          hash TEXT NOT NULL,
          source_mtime TEXT,
          captured_at TEXT NOT NULL,
          summary_path TEXT
        );
        """
    )
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(documents)").fetchall()
    }
    if "source_mtime" not in columns:
        connection.execute("ALTER TABLE documents ADD COLUMN source_mtime TEXT")
    return connection


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    value = value.lstrip("\ufeff")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def extract_text_file(path: Path) -> tuple[str, str]:
    text = normalize_text(path.read_text(encoding="utf-8-sig", errors="replace"))
    return title_from_markdown(text, path.stem), text


def extract_docx(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Unable to read DOCX text: {exc}") from exc

    root = ElementTree.fromstring(document)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = [
            node.text
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    text = normalize_text("\n".join(paragraphs))
    return (paragraphs[0][:80] if paragraphs else path.stem), text


def extract_pdf(path: Path) -> tuple[str, str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF extraction requires optional dependency 'pypdf'.") from exc

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = normalize_text("\n".join(pages))
    return path.stem, text


def extract_local_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return extract_text_file(path)
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    raise ValueError(f"Unsupported file type: {suffix}")


class TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.title = ""
        self._in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data.strip()
            return
        self.parts.append(data)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def capture_url_text(url: str) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": "personal-knowledge-capture/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get("content-type", "")
            body = response.read(2 * 1024 * 1024)
    except URLError as exc:
        raise RuntimeError(f"Unable to fetch URL: {exc}") from exc

    text = body.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or "<html" in text[:500].lower():
        parser = TextHTMLParser()
        parser.feed(text)
        extracted = parser.text()
        return parser.title.strip() or url, extracted
    return url, normalize_text(text)


def source_title(path: Path, title: str) -> str:
    return title.strip() or path.stem


def get_document(connection: sqlite3.Connection, source: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM documents WHERE path_or_url = ?",
        (source,),
    ).fetchone()


def upsert_document(
    connection: sqlite3.Connection,
    source: str,
    title: str,
    digest: str,
    captured_at: str,
    source_mtime: str | None = None,
    summary_path: str | None = None,
) -> None:
    existing = get_document(connection, source)
    if existing:
        connection.execute(
            """
            UPDATE documents
            SET title = ?, hash = ?, source_mtime = ?, captured_at = ?, summary_path = COALESCE(?, summary_path)
            WHERE path_or_url = ?
            """,
            (title, digest, source_mtime, captured_at, summary_path, source),
        )
    else:
        connection.execute(
            """
            INSERT INTO documents(path_or_url, title, hash, source_mtime, captured_at, summary_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source, title, digest, source_mtime, captured_at, summary_path),
        )


def command_add_watch(args: argparse.Namespace) -> int:
    path = expand_path(args.path)
    if not path.exists() or not path.is_dir():
        print(f"Refusing watch path that is not an existing directory: {path}", file=sys.stderr)
        return 2

    now = utc_now()
    with connect_db(args.state_dir) as connection:
        existing = connection.execute(
            "SELECT id FROM watch_paths WHERE path = ?",
            (str(path),),
        ).fetchone()
        if existing:
            connection.execute(
                "UPDATE watch_paths SET tags = COALESCE(?, tags) WHERE path = ?",
                (args.tags or None, str(path)),
            )
        else:
            connection.execute(
                """
                INSERT INTO watch_paths(path, tags, created_at, last_scanned_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(path), args.tags or "", now, now),
            )

    print(f"watch_path={path}")
    print(f"tags={args.tags or ''}")
    print("supported_file_types=.md,.markdown,.txt,.pdf,.docx")
    print("pdf_requires=pypdf")
    print("docx_supported=basic built-in text extraction")
    return 0


def iter_supported_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                paths.append(path)
        except (FileNotFoundError, PermissionError, OSError):
            continue
    return sorted(paths, key=lambda item: str(item).lower())


def scan_watch_paths(state_dir: Path, *, commit: bool) -> dict[str, Any]:
    paths = ensure_state_dirs(state_dir)
    rid = run_id()
    now = utc_now()
    items: list[CaptureItem] = []
    watched: list[str] = []

    with connect_db(state_dir) as connection:
        rows = connection.execute("SELECT * FROM watch_paths ORDER BY path").fetchall()
        for row in rows:
            root = Path(row["path"])
            watched.append(str(root))
            if not root.exists() or not root.is_dir():
                items.append(
                    CaptureItem(
                        source=str(root),
                        title=root.name,
                        status="skipped",
                        reason="registered watch path no longer exists",
                    )
                )
                continue

            for path in iter_supported_files(root):
                source = str(path.resolve())
                try:
                    digest = sha256_file(path)
                    source_mtime = datetime.fromtimestamp(
                        path.stat().st_mtime,
                        timezone.utc,
                    ).replace(microsecond=0).isoformat()
                    existing = get_document(connection, source)
                    if (
                        existing
                        and existing["hash"] == digest
                        and existing["source_mtime"] == source_mtime
                    ):
                        continue
                    title, text = extract_local_text(path)
                    status = "modified" if existing else "new"
                    captured_at = utc_now()
                    if commit:
                        upsert_document(
                            connection,
                            source=source,
                            title=source_title(path, title),
                            digest=digest,
                            captured_at=captured_at,
                            source_mtime=source_mtime,
                        )
                    items.append(
                        CaptureItem(
                            source=source,
                            title=source_title(path, title),
                            status=status,
                            digest=digest,
                            captured_at=captured_at,
                            text=text[:MAX_CAPTURE_CHARS],
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - report per-file extraction failure.
                    items.append(
                        CaptureItem(
                            source=source,
                            title=path.name,
                            status="skipped",
                            reason=str(exc),
                        )
                    )

            if commit:
                connection.execute(
                    "UPDATE watch_paths SET last_scanned_at = ? WHERE id = ?",
                    (now, row["id"]),
                )

    run = {
        "run_id": rid,
        "created_at": now,
        "watch_paths": watched,
        "items": [item.__dict__ for item in items],
    }
    run_path = paths["runs"] / f"{rid}-scan.json"
    run["run_path"] = str(run_path)
    run_path.write_text(json.dumps(run, indent=2), encoding="utf-8")
    return run


def command_scan(args: argparse.Namespace) -> int:
    run = scan_watch_paths(args.state_dir, commit=False)
    items = run["items"]
    print(f"run={run['run_path']}")
    print(f"watch_paths={len(run['watch_paths'])}")
    print(f"new={sum(1 for item in items if item['status'] == 'new')}")
    print(f"modified={sum(1 for item in items if item['status'] == 'modified')}")
    print(f"skipped={sum(1 for item in items if item['status'] == 'skipped')}")
    return 0


def concise_summary(text: str) -> str:
    text = normalize_text(text)
    if not text:
        return "No extractable text was found."
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    candidate = paragraphs[0] if paragraphs else text
    candidate = re.sub(r"^#{1,6}\s+", "", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if len(candidate) > MAX_NOTE_CHARS:
        candidate = candidate[:MAX_NOTE_CHARS].rstrip() + "..."
    return candidate


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def write_summary_note(state_dir: Path, run: dict[str, Any]) -> Path:
    paths = ensure_state_dirs(state_dir)
    note_path = paths["notes"] / f"{date.today().isoformat()}-summary.md"
    changed = [
        item
        for item in run["items"]
        if item.get("status") in {"new", "modified"}
    ]
    skipped = [item for item in run["items"] if item.get("status") == "skipped"]

    lines = [
        "# Summary",
        "",
        f"- Run: `{run['run_id']}`",
        f"- Created: `{run['created_at']}`",
        f"- Watch paths: {', '.join(f'`{path}`' for path in run['watch_paths']) or 'None'}",
        f"- New files: {sum(1 for item in changed if item['status'] == 'new')}",
        f"- Modified files: {sum(1 for item in changed if item['status'] == 'modified')}",
        "",
        "## New Files",
        "",
    ]
    new_items = [item for item in changed if item["status"] == "new"]
    if new_items:
        for item in new_items:
            lines.append(f"- `{item['title']}` from `{item['source']}`")
    else:
        lines.append("No new files detected.")

    lines.extend(["", "## Key Insights", ""])
    if changed:
        for item in changed:
            lines.append(f"- **{item['title']}**: {concise_summary(item.get('text', ''))}")
    else:
        lines.append("No new or modified source text was available to summarize.")

    lines.extend(["", "## Actionable Notes", ""])
    if changed:
        lines.append("- Review the captured source references before using these notes as final research output.")
        lines.append("- Ask Codex to refine this draft into a deeper synthesis when richer interpretation is needed.")
    else:
        lines.append("- No follow-up actions were generated from this scan.")

    lines.extend(["", "## Open Questions", ""])
    if skipped:
        for item in skipped:
            lines.append(f"- Could not capture `{item['source']}`: {item.get('reason', 'unknown reason')}")
    else:
        lines.append("- No extraction gaps were reported.")

    lines.extend(["", "## Source References", ""])
    if changed:
        lines.append("| Status | Title | Source | Hash |")
        lines.append("| --- | --- | --- | --- |")
        for item in changed:
            lines.append(
                f"| {item['status']} | {markdown_escape(item['title'])} | "
                f"`{markdown_escape(item['source'])}` | `{item.get('digest', '')}` |"
            )
    else:
        lines.append("No source references were added in this run.")

    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with connect_db(state_dir) as connection:
        for item in changed:
            connection.execute(
                "UPDATE documents SET summary_path = ? WHERE path_or_url = ?",
                (str(note_path), item["source"]),
            )
    return note_path


def command_summarize(args: argparse.Namespace) -> int:
    run = scan_watch_paths(args.state_dir, commit=True)
    note_path = write_summary_note(args.state_dir, run)
    items = run["items"]
    print(f"summary={note_path}")
    print(f"new={sum(1 for item in items if item['status'] == 'new')}")
    print(f"modified={sum(1 for item in items if item['status'] == 'modified')}")
    print(f"skipped={sum(1 for item in items if item['status'] == 'skipped')}")
    return 0


def command_capture_url(args: argparse.Namespace) -> int:
    now = utc_now()
    try:
        title, text = capture_url_text(args.url)
    except Exception as exc:  # noqa: BLE001 - CLI should report a stable error.
        print(str(exc), file=sys.stderr)
        return 2

    digest = sha256_text(text)
    with connect_db(args.state_dir) as connection:
        existing = get_document(connection, args.url)
        status = "modified" if existing and existing["hash"] != digest else "new"
        if existing and existing["hash"] == digest:
            status = "unchanged"
        if status != "unchanged":
            upsert_document(connection, args.url, title, digest, now, source_mtime=now)

    print(f"url={args.url}")
    print(f"title={title}")
    print(f"status={status}")
    print(f"hash={digest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture local knowledge sources into Markdown notes.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_watch = subparsers.add_parser("add-watch", help="Register a local folder for later scans.")
    add_watch.add_argument("--path", required=True, help="Existing local folder to scan.")
    add_watch.add_argument("--tags", default="", help="Optional comma-separated tags for this watch path.")
    add_watch.set_defaults(func=command_add_watch)

    scan = subparsers.add_parser("scan", help="Scan registered watch paths for new or modified files.")
    scan.set_defaults(func=command_scan)

    summarize = subparsers.add_parser("summarize", help="Scan and write a dated Markdown summary note.")
    summarize.set_defaults(func=command_summarize)

    capture_url = subparsers.add_parser("capture-url", help="Capture text from an explicitly provided URL.")
    capture_url.add_argument("--url", required=True)
    capture_url.set_defaults(func=command_capture_url)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
