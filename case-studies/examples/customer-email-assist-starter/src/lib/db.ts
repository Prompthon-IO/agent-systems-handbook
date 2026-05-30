import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import Database from "better-sqlite3";

const DEFAULT_STATE_DIR = path.join(
  os.homedir(),
  ".codex",
  "state",
  "customer-email-assist",
);

const DEFAULT_DB_PATH = path.join(DEFAULT_STATE_DIR, "customer-email-assist.sqlite3");

export function resolveDbPath(inputPath?: string): string {
  if (inputPath) {
    return path.resolve(inputPath);
  }
  if (process.env.CUSTOMER_EMAIL_ASSIST_DB_PATH) {
    return path.resolve(process.env.CUSTOMER_EMAIL_ASSIST_DB_PATH);
  }
  return DEFAULT_DB_PATH;
}

export function deleteDatabaseFiles(inputPath?: string): string {
  const filePath = resolveDbPath(inputPath);
  for (const candidate of [filePath, `${filePath}-wal`, `${filePath}-shm`]) {
    if (fs.existsSync(candidate)) {
      fs.rmSync(candidate, { force: true });
    }
  }
  return filePath;
}

function ensureDirectory(filePath: string): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

export function openDatabase(inputPath?: string): Database.Database {
  const filePath = resolveDbPath(inputPath);
  ensureDirectory(filePath);

  const db = new Database(filePath);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.exec(`
    CREATE TABLE IF NOT EXISTS customers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL DEFAULT '',
      description TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'ignored')),
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      last_seen_at TEXT
    );

    CREATE TABLE IF NOT EXISTS issues (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
      gmail_thread_id TEXT NOT NULL UNIQUE,
      received_at TEXT NOT NULL,
      classification TEXT NOT NULL CHECK (
        classification IN ('query', 'complaint', 'refund_request', 'billing_issue', 'handoff_required')
      ),
      summary TEXT NOT NULL,
      urgency TEXT NOT NULL CHECK (urgency IN ('normal', 'high')),
      original_message_text TEXT NOT NULL,
      draft_template_json TEXT,
      draft_reply_html TEXT,
      draft_reply_text TEXT,
      action_suggestion TEXT NOT NULL CHECK (
        action_suggestion IN ('send_reply', 'manual_follow_up', 'handoff')
      ),
      issue_status TEXT NOT NULL CHECK (
        issue_status IN ('draft_ready', 'approved_to_send', 'resolved', 'sync_error')
      ),
      approved_at TEXT,
      sent_at TEXT,
      resolved_at TEXT,
      gmail_last_inbound_message_id TEXT NOT NULL,
      gmail_last_outbound_message_id TEXT,
      last_synced_at TEXT NOT NULL,
      error_message TEXT
    );
    CREATE INDEX IF NOT EXISTS issues_customer_id_idx ON issues(customer_id);
    CREATE INDEX IF NOT EXISTS issues_status_idx ON issues(issue_status);
    CREATE INDEX IF NOT EXISTS customers_status_idx ON customers(status);
  `);

  return db;
}
