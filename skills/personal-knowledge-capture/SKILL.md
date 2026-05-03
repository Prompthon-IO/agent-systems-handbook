---
name: personal-knowledge-capture
description: Capture local or explicitly provided web knowledge sources into cited Markdown notes. Use when a user asks Codex to watch a research folder, register local folders for later scans, summarize new or modified local Markdown/TXT/PDF/DOCX files, capture a provided URL, maintain SQLite state for personal knowledge capture, or generate searchable source-grounded daily notes.
---

# Personal Knowledge Capture

Use this skill to maintain local-first personal knowledge notes from user-approved sources. Register folders only when the user names them, scan registered folders on demand, extract text from supported file types, and write cited Markdown notes.

For the human-facing overview, read `README.md`. For supported file type details, read `references/supported-file-types.md` when extraction behavior matters.

## Safety Rules

- Scan only folders the user explicitly names or previously registered with `add-watch`.
- Do not upload local files to external services unless the user explicitly asks and credentials are available.
- Preserve source files exactly; never move, rewrite, delete, or rename them.
- Keep runtime databases, scan artifacts, and generated notes outside git unless the user explicitly asks for sample artifacts.
- Ground generated notes in source references. Do not present uncited claims as coming from the captured files.
- Treat `capture-url` as opt-in only: fetch only URLs the user explicitly provides.

## Default Workflow

1. Register a watch path with `scripts/personal_knowledge_capture.py add-watch --path <folder>`.
2. Run `scripts/personal_knowledge_capture.py scan` when the user wants a detection preview only; this does not mark files as captured.
3. Run `scripts/personal_knowledge_capture.py summarize` when the user wants a dated Markdown note; this command performs its own scan.
4. Review the generated note and refine summaries with Codex when deeper synthesis is needed.
5. Report source paths, skipped files, and the note path to the user.

## Commands

Resolve `scripts/personal_knowledge_capture.py` relative to this skill directory. When running from an installed Codex copy, that is usually:

```bash
python3 scripts/personal_knowledge_capture.py add-watch --path "$HOME/research" --tags "ai,research"
```

Scan registered watch paths:

```bash
python3 scripts/personal_knowledge_capture.py scan
```

Scan and write today's Markdown summary:

```bash
python3 scripts/personal_knowledge_capture.py summarize
```

Capture an explicitly provided URL:

```bash
python3 scripts/personal_knowledge_capture.py capture-url --url "https://example.com/article"
```

Use `--state-dir <path>` only when a user asks to place runtime state somewhere specific.

## Persistence

The helper stores local runtime artifacts under:

```text
~/.codex/state/personal-knowledge-capture/
  knowledge_capture.db
  runs/
  knowledge-notes/
```

SQLite tables:

```sql
watch_paths(id, path, tags, created_at, last_scanned_at)
documents(id, path_or_url, title, hash, source_mtime, captured_at, summary_path)
```

`source_mtime` is an implementation addition beyond the base issue schema. It stores
the source file's last-modified timestamp so the scanner can skip files whose
content hash and mtime are both unchanged, reducing redundant re-extraction.

## Markdown Output

Daily summaries are written to:

```text
knowledge-notes/YYYY-MM-DD-summary.md
```

The generated note must keep this structure:

```md
# Summary

## New Files

## Key Insights

## Actionable Notes

## Open Questions

## Source References
```

If Codex rewrites or enriches the summary, preserve the section headings and keep every source-grounded point tied to `Source References`.

## Supported Sources

- Markdown: `.md`, `.markdown`
- Plain text: `.txt`
- DOCX: basic built-in text extraction from `word/document.xml`
- PDF: supported when the optional `pypdf` dependency is installed
- URLs: supported only through explicit `capture-url --url <url>`

For unsupported or failed extraction, report the skipped source and reason instead of silently dropping it.

## Response Pattern

When reporting results to the user, include:

- registered or scanned paths
- number of new, modified, and skipped sources
- generated note path
- skipped files and extraction reasons
- source-reference expectations for any summary text
