# SQLite Schema

Use a local SQLite database for persistent state. The default path is `price-watcher.sqlite3` in the current workspace unless the user supplies another path.

## Tables

```sql
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
```

## Notes

- Store the user's natural-language product query in `items.query`.
- Store a concise canonical product name in `items.normalized_name` once a confident match exists.
- Keep `items.target_price` numeric and currency-neutral in the v1 schema. Report the inferred currency in prose when it matters.
- Allow multiple source rows per item.
- Update `sources.last_checked_at` every time a source is attempted, even if extraction fails and the failure only appears in the Markdown report.
- Append to `price_checks`; do not overwrite history.
