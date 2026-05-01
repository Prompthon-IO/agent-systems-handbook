---
name: daily-news-watcher
description: Persistent daily news monitoring backed by local SQLite and Markdown reports. Use when a user asks Codex to track named publications, fetch the last N hours of news, summarize recent articles by topic, deduplicate articles across runs, or maintain a personal newsroom that survives across sessions.
---

# Daily News Watcher

For a student-facing explanation of why this package exists and how the
end-to-end workflow fits into the handbook, read `README.md` first. This file
is the invocation contract for Codex.

## Overview

Use this skill to operate a persistent personal news watcher. The skill keeps
a list of named sources in SQLite, fetches recent articles from RSS/Atom feeds
(with an optional Playwright fallback for pages without usable feeds),
deduplicates results by canonical URL and content hash, summarizes them, and
writes a Markdown report per run.

The skill has two distinct workflows: **add sources** and **fetch and
summarize**. Treat them as separate user intents and surface them as separate
commands.

## Safety Rules

- Only register and fetch public sources. Refuse `file://`, internal hostnames,
  and anything that requires auth headers, cookies, or login flows.
- Never bypass paywalls, captchas, or other access controls.
- Never store browsing credentials, session cookies, or auth tokens.
- One failing source must not abort the whole run. Record the failure on the
  `runs` row and continue with the next source.
- The runtime database, logs, and generated reports live under
  `~/.codex/state/daily-news-watcher/` and stay out of git unless the user
  explicitly asks to commit example artifacts.
- Honor the readable rules in `references/fetch-rules.md`.

## Workflow A - Add Sources

Trigger when the user names publications to track ("add BBC AI, The Verge AI,
and OpenAI Blog to my daily news watcher").

1. For each name, resolve to a URL using `references/known-sources.csv`. If
   the publication is not known, ask the user for an explicit `--url`.
2. Validate that the URL is a public `http(s)` URL.
3. Probe reachability with a short HTTP GET. Surface unreachable sources as a
   warning but still allow registration if the user insists.
4. Insert the source into `sources` with tags. Existing rows with the same
   name are updated rather than duplicated.
5. Echo the resolved URL, type, and tags so the user can confirm.

## Workflow B - Fetch And Summarize

Trigger when the user asks for a daily digest ("fetch the last 24 hours of AI
news").

1. Read all rows from `sources`.
2. For each source, fetch via RSS/Atom first. If the response is not a feed
   and `--use-playwright` is set, fall back to a Playwright render.
3. Normalize each article (canonical URL, stripped HTML summary, parsed
   `published_at`) and skip duplicates by URL or content hash.
4. Apply `--hours` and `--topic` filters.
5. Insert kept articles into `articles` and stamp the source with
   `last_checked_at`.
6. Write a Markdown report to
   `~/.codex/state/daily-news-watcher/reports/daily-news/YYYY-MM-DD-<topic>.md`
   that lists sources checked, articles included, summaries, links, and any
   skipped or error notes.
7. Update the `runs` row with `finished_at` and a status of `ok`, `partial`,
   `all_sources_failed`, or `no_sources`.

## Commands

Resolve `scripts/daily_news_watcher.py` relative to this skill directory. When
running from an installed Codex copy, that is usually
`~/.codex/skills/daily-news-watcher/scripts/daily_news_watcher.py`.

Add a known publication:

```bash
python3 scripts/daily_news_watcher.py add-source --name "BBC AI"
```

Add a custom source by URL:

```bash
python3 scripts/daily_news_watcher.py add-source \
  --name "Example AI Blog" \
  --url "https://example.com/feed.xml" \
  --tags "AI;research"
```

List or remove sources:

```bash
python3 scripts/daily_news_watcher.py list-sources
python3 scripts/daily_news_watcher.py remove-source --id 3
```

Fetch the last 24 hours of AI news:

```bash
python3 scripts/daily_news_watcher.py fetch --hours 24 --topic AI
```

Fetch with the optional Playwright fallback enabled:

```bash
python3 scripts/daily_news_watcher.py fetch --hours 24 --topic AI --use-playwright
```

Show recent runs:

```bash
python3 scripts/daily_news_watcher.py runs --limit 10
```

## Persistence

The SQLite database lives at:

```text
~/.codex/state/daily-news-watcher/news.sqlite
```

Schema:

```sql
sources(id, name, url, type, tags, created_at, last_checked_at)
articles(id, source_id, title, url, published_at, fetched_at, summary, hash)
runs(id, topic, started_at, finished_at, status)
```

`articles.url` and `articles.hash` are unique, so reruns naturally deduplicate
across sessions.

## Outputs

```text
~/.codex/state/daily-news-watcher/
  news.sqlite
  reports/daily-news/YYYY-MM-DD-<topic>.md
  logs/<run_id>-fetch.json
```

Do not commit runtime databases, logs, or reports unless the user explicitly
asks for sample artifacts.

## Response Pattern

When reporting fetch results to the user, include:

- run id and status
- number of sources checked, with how many had errors
- number of articles included after dedupe and filtering
- the report path
- a short rewritten summary of the most relevant articles (Codex should
  rewrite the deterministic snippets into readable prose)
- any source-level errors that should be retried later

When reporting source-management results, include the resolved URL, the
inferred type, and any reachability warning.
