import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { openDatabase } from "@/lib/db";
import {
  createCustomer,
  listCustomerReviewQueue,
  listCustomers,
  listIssues,
  reviewCustomer,
  updateIssue,
  upsertIssueRecord,
} from "@/lib/repository";

describe("repository queries", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "customer-email-assist-repo-"));
  const dbPath = path.join(root, "repo.sqlite3");

  afterAll(() => {
    rmSync(root, { recursive: true, force: true });
  });

  it("filters and paginates issues server-side", () => {
    const db = openDatabase(dbPath);
    db.exec("DELETE FROM issues; DELETE FROM customers;");
    const approved = createCustomer(db, {
      email: "approved@example.com",
      displayName: "Approved Customer",
      description: "",
      status: "approved",
    });
    const pending = createCustomer(db, {
      email: "pending@example.com",
      displayName: "Pending Customer",
      description: "",
      status: "pending",
    });

    upsertIssueRecord(db, {
      gmailThreadId: "thread-a",
      gmailLastInboundMessageId: "msg-a",
      customerId: approved.id,
      receivedAt: "2026-05-29T12:00:00Z",
      classification: "refund_request",
      summary: "Refund request",
      urgency: "normal",
      originalMessageText: "Refund request body",
      actionSuggestion: "send_reply",
      issueStatus: "draft_ready",
    });
    upsertIssueRecord(db, {
      gmailThreadId: "thread-b",
      gmailLastInboundMessageId: "msg-b",
      customerId: pending.id,
      receivedAt: "2026-05-30T12:00:00Z",
      classification: "query",
      summary: "General question",
      urgency: "high",
      originalMessageText: "Question body",
      actionSuggestion: "send_reply",
      issueStatus: "resolved",
    });
    upsertIssueRecord(db, {
      gmailThreadId: "thread-c",
      gmailLastInboundMessageId: "msg-c",
      customerId: approved.id,
      receivedAt: "2026-05-31T12:00:00Z",
      classification: "complaint",
      summary: "Complaint follow-up",
      urgency: "high",
      originalMessageText: "Complaint body",
      actionSuggestion: "manual_follow_up",
      issueStatus: "approved_to_send",
    });

    const result = listIssues(db, {
      page: 1,
      pageSize: 10,
      classification: ["refund_request", "complaint"],
      includeResolved: true,
    });

    expect(result.items).toHaveLength(2);
    expect(result.total).toBe(2);
    expect(result.items.map((item) => item.classification)).toEqual([
      "complaint",
      "refund_request",
    ]);
    expect(result.summaryCounts.resolved).toBe(1);
  });

  it("returns pending customers for review and persists approve or ignore actions", () => {
    const db = openDatabase(dbPath);
    db.exec("DELETE FROM issues; DELETE FROM customers;");
    const queued = createCustomer(db, {
      email: "review@example.com",
      displayName: "Review Me",
      description: "needs verification",
      status: "pending",
    });

    let queue = listCustomerReviewQueue(db, { page: 1, pageSize: 10 });
    expect(queue.items.map((item) => item.email)).toContain("review@example.com");

    reviewCustomer(db, queued.id, {
      status: "ignored",
      description: "ignore future cold outreach",
    });

    queue = listCustomerReviewQueue(db, { page: 1, pageSize: 10 });
    expect(queue.items.map((item) => item.email)).not.toContain("review@example.com");
  });

  it("lists approved customers by default and includes ignored only when requested", () => {
    const db = openDatabase(dbPath);
    db.exec("DELETE FROM issues; DELETE FROM customers;");

    createCustomer(db, {
      email: "approved@example.com",
      displayName: "Approved",
      description: "",
      status: "approved",
    });
    createCustomer(db, {
      email: "ignored@example.com",
      displayName: "Ignored",
      description: "",
      status: "ignored",
    });
    createCustomer(db, {
      email: "pending@example.com",
      displayName: "Pending",
      description: "",
      status: "pending",
    });

    const approvedOnly = listCustomers(db, {
      page: 1,
      pageSize: 10,
      statuses: ["approved"],
    });
    expect(approvedOnly.items.map((item) => item.email)).toEqual(["approved@example.com"]);

    const approvedAndIgnored = listCustomers(db, {
      page: 1,
      pageSize: 10,
      statuses: ["approved", "ignored"],
    });
    expect(approvedAndIgnored.items.map((item) => item.email)).toEqual([
      "ignored@example.com",
      "approved@example.com",
    ]);
  });

  it("revokes send approval back to draft review", () => {
    const db = openDatabase(dbPath);
    db.exec("DELETE FROM issues; DELETE FROM customers;");
    const customer = createCustomer(db, {
      email: "approved@example.com",
      displayName: "Approved",
      description: "",
      status: "approved",
    });
    const issueId = upsertIssueRecord(db, {
      gmailThreadId: "thread-approved",
      gmailLastInboundMessageId: "msg-approved",
      customerId: customer.id,
      receivedAt: "2026-05-30T12:00:00Z",
      classification: "query",
      summary: "Question",
      urgency: "normal",
      originalMessageText: "Question body",
      actionSuggestion: "send_reply",
      issueStatus: "approved_to_send",
    });

    updateIssue(db, issueId, { action: "revoke_send_approval" });

    const row = db
      .prepare("SELECT issue_status, approved_at FROM issues WHERE id = ?")
      .get(issueId) as { issue_status: string; approved_at: string | null };
    expect(row.issue_status).toBe("draft_ready");
    expect(row.approved_at).toBeNull();
  });
});
