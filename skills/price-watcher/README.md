# Price Watcher

## Demo Video

Watch a short walkthrough of this skill: [Price Watcher demo](https://youtu.be/i9qOsDBVg70).

## Why This Skill Exists

This package is a Practitioner-facing workflow example for persistent product
price tracking.

It exists because "watch this product and tell me when it drops below my price"
sounds like a simple prompt, but it needs durable local state, repeated source
checks, product matching, price history, and report generation across sessions.
A one-off chat answer cannot reliably remember watched items or compare today
against previous checks.

The package demonstrates a better pattern:

- accept natural-language product requests
- discover product sources instead of requiring pasted URLs
- normalize likely product matches across retailers
- store watched items and source URLs in SQLite
- append price observations over time
- generate lowest-price-first Markdown reports

## Who It Is For

This skill is for students, contributors, and operators who want to understand
what a real Codex-compatible local workflow looks like when persistent state,
browser-assisted lookup, and user-facing reports matter.

It is most useful for requests such as:

- watch a laptop, appliance, or other product until it drops below a target price
- check all active watched items and summarize the best current prices
- compare observed prices against the last recorded check
- produce a local Markdown report that can be reviewed before any notification
  workflow is added

## End-to-End Workflow

The workflow is intentionally local-first and source-aware:

1. Parse the user's natural-language product request and target price.
2. Store the original watched query in SQLite.
3. Discover matching product pages across multiple sources.
4. Normalize product identity so likely same-product matches can be deduplicated.
5. Save source URLs for the watched item.
6. Check known sources on demand, using browser automation where normal page
   rendering is needed.
7. Extract and normalize visible prices and currencies.
8. Append price observations to history.
9. Compare current prices against the previous check and target threshold.
10. Write a Markdown report to `price-reports/YYYY-MM-DD.md`.

That is the main teaching point of the package. The skill is not just "scrape a
URL." It is a persistent watch-list workflow with product discovery, historical
comparison, and reportable state.

## What The Package Actually Does

The package currently focuses on the v1 price-watching loop from issue #35:

- natural-language watched-item setup
- SQLite persistence using `items`, `sources`, and `price_checks`
- multiple source URLs per watched product
- helper commands for adding items, adding sources, recording prices, and
  writing reports
- reference guidance for source discovery, product normalization, and price
  parsing
- Markdown reports sorted by the lowest currently observed price

The deterministic helper script is `scripts/price_watcher.py`. It manages local
state and report generation. Live product discovery and Playwright/browser use
are described in `SKILL.md` so Codex can apply the right runtime tools in the
execution environment.

## What It Does Not Do

This package does not:

- require users to manually provide product URLs
- buy products, add items to cart, reserve inventory, or initiate checkout
- bypass account gates, CAPTCHAs, paywalls, bot checks, or other access controls
- treat Amazon pages as available unless they are normally browser-accessible
- send notifications in v1
- commit runtime SQLite databases or generated reports by default

## How To Read It In The Handbook

Treat this package as a Practitioner example of a persistent, browser-adjacent
local workflow:

- `README.md` explains the human story and end-to-end process
- `SKILL.md` explains when Codex should invoke the package
- `scripts/price_watcher.py` implements deterministic SQLite and report helpers
- `references/schema.md` documents the local database shape
- `references/source-discovery.md` describes product matching and deduplication
- `references/price-parsing.md` describes conservative price extraction rules

If you are a student reading the repo, the main lesson is:

1. durable agent workflows need explicit local state
2. product matching should start from user intent, not fixed URLs
3. recurring checks should append history and produce reviewable reports
4. commerce-adjacent automation needs clear safety and access boundaries
