# Supported File Types

This skill is local-first. Extraction should happen on the user's machine and should preserve source file paths for later review.

## Direct Text

- `.md`
- `.markdown`
- `.txt`

Read these files as UTF-8 with replacement for invalid bytes. Use the first Markdown heading as the title when available; otherwise use the file stem.

## DOCX

`.docx` files are ZIP containers. The helper extracts paragraph text from `word/document.xml` with Python's standard library. This is sufficient for basic notes, but it does not preserve comments, tracked changes, tables, headers, footers, or embedded media.

## PDF

`.pdf` files require the optional `pypdf` dependency. If it is not installed or a PDF has no extractable text, report the source as skipped with the reason. Do not fail the whole scan because one PDF cannot be read.

## URLs

URLs are opt-in only. Fetch a URL only when the user provides it explicitly. Do not crawl linked pages. Store the URL as the source reference.

## Unsupported Inputs

Skip unsupported files and report the reason. Do not silently infer content from filenames alone, and do not upload local files to external services unless the user explicitly asks and credentials are available.
