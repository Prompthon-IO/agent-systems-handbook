import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { deleteDatabaseFiles, openDatabase } from "@/lib/db";

describe("database helpers", () => {
  it("deletes the sqlite database plus wal and shm files", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "customer-email-assist-db-"));
    const dbPath = path.join(root, "customer-email-assist.sqlite3");

    const db = openDatabase(dbPath);
    db.prepare(
      `
        INSERT INTO customers (email, display_name, description, status, created_at, updated_at, last_seen_at)
        VALUES (?, ?, '', 'pending', '2026-01-01T00:00:00.000Z', '2026-01-01T00:00:00.000Z', '2026-01-01T00:00:00.000Z')
      `,
    ).run("tester@example.com", "Tester");
    db.close();

    fs.writeFileSync(`${dbPath}-wal`, "");
    fs.writeFileSync(`${dbPath}-shm`, "");

    deleteDatabaseFiles(dbPath);

    expect(fs.existsSync(dbPath)).toBe(false);
    expect(fs.existsSync(`${dbPath}-wal`)).toBe(false);
    expect(fs.existsSync(`${dbPath}-shm`)).toBe(false);
  });
});
