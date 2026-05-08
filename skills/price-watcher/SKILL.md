---
name: price-watcher
description: Persistent product price tracking for natural-language product requests. Use when a user asks to watch, track, monitor, compare, or report prices for a product, especially with a target price or threshold such as "Watch MacBook Pro M3 14-inch and tell me if it drops below $1200." Supports source discovery, Playwright/browser product checks, SQLite history, threshold comparison, and Markdown price reports.
---

# Price Watcher

Track product prices from natural-language product descriptions. Do not require the user to provide product URLs. Store the watch query, discover and refresh multiple source URLs, save price history in SQLite, and write reports to the configured report directory.

## Quick Start

Resolve paths relative to this skill directory. Use `scripts/price_watcher.py` for deterministic local state operations:

```bash
cd skills/price-watcher
python3 scripts/price_watcher.py init
python3 scripts/price_watcher.py add "Watch MacBook Pro M3 14-inch and notify me if it drops below $1200"
python3 scripts/price_watcher.py sources add --item-id 1 --site "Best Buy" --url "https://..."
python3 scripts/price_watcher.py record --item-id 1 --source-id 1 --price 1199.99 --currency USD
python3 scripts/price_watcher.py report
```

Default runtime paths:

- State root: `~/.codex/state/price-watcher/`, override with `PRICE_WATCHER_STATE`
- Database: `~/.codex/state/price-watcher/price-watcher.sqlite3`
- Reports: `~/.codex/state/price-watcher/price-reports/YYYY-MM-DD.md`

Keep runtime databases and generated reports out of git unless the user explicitly asks to commit examples.

## Workflow A: Add Watched Item

1. Parse the user's request into:
   - `query`: the product description to keep watching.
   - `target_price`: the numeric threshold if present.
   - `currency`: infer from symbols or wording; default to the user's locale when unclear.
2. Store the original product query, not a single fixed URL.
3. Search across multiple sources using web search, retailer search pages, or shopping/search APIs available in the current environment.
4. Normalize likely product matches:
   - canonical product name
   - brand/model/generation/size/storage/color or other important attributes
   - marketplace or retailer site
   - product URL
5. Deduplicate likely same-product matches by comparing normalized names and attributes. Prefer exact model/generation matches over merely similar products.
6. Add multiple source URLs for the item. Do not ask the user to manually provide URLs unless source discovery fails and the user wants to help.

Use `python3 scripts/price_watcher.py add "<request>"` after parsing to create the SQLite item, then add discovered source URLs with `sources add`.

## Workflow B: Check Prices

For each active item:

1. Load active items and known sources from SQLite.
2. Refresh source discovery when:
   - no sources exist,
   - known sources fail repeatedly,
   - the user asks for broader coverage,
   - a product appears discontinued or out of stock everywhere.
3. Query all known sources. Use direct HTTP only when normal access works. Use Playwright/browser automation for pages that need client-side rendering.
4. Respect access controls:
   - Amazon scraping is allowed only through normal browser-accessible pages.
   - Do not bypass login, bot challenges, paywalls, CAPTCHAs, or account gates.
   - Do not purchase items, add to cart, reserve inventory, or initiate checkout.
5. Extract price, currency, availability when visible, and failure/skipped notes.
6. Normalize price and currency before storage. If conversion rates are needed and unavailable, keep the observed currency and do not compare across currencies as exact values.
7. Save each successful observation to `price_checks`.
8. Compare against the previous check for the same item/source and the item target price only when currencies are comparable.
9. Generate a Markdown report with `report`.

## Report Requirements

Write reports to the configured `price-reports/YYYY-MM-DD.md` directory. Sort items lowest-price-first by the best current observed price. Include:

- item query and normalized name
- target price and whether the best price meets it
- source links
- observed prices and currencies
- lowest price across sources
- changes since the previous check
- failed or skipped source notes

Treat notifications as out of scope for v1. For a request like "notify me," store the threshold and write report status; do not send messages unless a later version adds a notification channel.

## SQLite Schema

Use this schema exactly unless the user asks for an extension:

```sql
items(id, query, normalized_name, target_price, created_at, active)
sources(id, item_id, site, url, last_checked_at)
price_checks(id, item_id, source_id, price, currency, checked_at)
```

See `references/schema.md` for column meanings and operational notes.

## Price Extraction

Prefer structured data in this order:

1. JSON-LD product offers
2. Open Graph/product meta tags
3. retailer page state JSON
4. visible DOM text near product title or buy box

Use `references/source-discovery.md` for source discovery and normalization heuristics. Use `references/price-parsing.md` for price parsing rules.

## Failure Handling

Record failed or skipped sources in the report even when no price can be stored. Common notes:

- `blocked: login required`
- `skipped: CAPTCHA or bot challenge`
- `skipped: checkout/cart-only price`
- `failed: price not visible`
- `failed: page unavailable`

Do not invent prices. If a page shows a range, store the lowest visible purchasable price only when the report clearly states it was a range.
