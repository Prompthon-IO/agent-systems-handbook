# Daily News Watcher

## Why This Skill Exists

This package is a Practitioner-facing example of a persistent local workflow.

A "daily news roundup" sounds like something a chat answer can solve, but as
soon as you want it to remember your sources, dedupe across days, and keep a
history of what it has already shown you, the request stops being a one-shot
prompt. It needs state that survives between sessions.

The package demonstrates the shape that pattern takes inside a Codex skill:

- a small SQLite database that persists sources, articles, and runs
- deterministic helpers for fetching, parsing, deduplicating, and summarizing
- readable rule files instead of hidden heuristics
- a Markdown report per run that the user can read or share
- explicit safety boundaries around what the skill is willing to fetch

## Who It Is For

This skill is for students, contributors, and operators who want to see what a
real Codex-compatible local workflow looks like when persistence matters.

It is most useful for requests such as:

- track a handful of named publications over time
- pull the last 24 hours of AI news into a single Markdown digest
- keep a personal newsroom that does not silently re-show old articles
- learn how SQLite, deterministic scripts, and agent reasoning fit together

## End-to-End Workflow

The workflow is intentionally split into two user intents:

1. **Add sources.** The user names publications they want to track. The skill
   resolves names to feed URLs (using a small known-sources table), validates
   each URL, and inserts it into the local database.
2. **Fetch and summarize.** The user asks for a digest with a topic and a time
   window. The skill fetches each source, parses RSS or Atom (with an optional
   Playwright fallback for pages without feeds), deduplicates by canonical URL
   and content hash, applies the topic and time filters, writes a Markdown
   report, and stamps the run in the database.

The agent is expected to rewrite the deterministic snippets into readable
prose in its final reply. The script supplies the data scaffolding; the model
supplies the language.

## What The Package Actually Does

- Stores sources, articles, and runs in `~/.codex/state/daily-news-watcher/news.sqlite`.
- Fetches feeds with stdlib `urllib` and parses them with `xml.etree`. If the
  optional `feedparser` package is installed, it is used automatically. If
  `playwright` is installed and `--use-playwright` is passed, it is used as a
  fallback for non-feed pages.
- Canonicalizes URLs (strips `utm_*`, `gclid`, etc.) and computes a SHA-256
  content hash so the same article does not appear in two reports.
- Writes a Markdown report per run under
  `reports/daily-news/YYYY-MM-DD-<topic>.md`.

## What It Does Not Do

This package does not:

- bypass paywalls, captchas, or login flows
- store cookies, auth headers, or session data
- abort the whole run when one source fails
- send notifications or push to external services in v1

## How To Read It In The Handbook

Treat this package as a Practitioner example of a local, persistence-heavy
workflow:

- `README.md` explains the human story and the two-intent workflow
- `SKILL.md` is the invocation contract for Codex
- `scripts/daily_news_watcher.py` implements the deterministic helper
- `references/known-sources.csv` resolves common publication names to URLs
- `references/fetch-rules.md` documents the safety and behavior rules

If you are a student reading the repo, the main lesson is:

1. some workflows fundamentally need state that outlives a single chat
2. SQLite is enough for that state when the workflow is local-first
3. a good skill package keeps the deterministic pieces (fetching, dedupe,
   storage) in scripts and lets the agent handle the language work
