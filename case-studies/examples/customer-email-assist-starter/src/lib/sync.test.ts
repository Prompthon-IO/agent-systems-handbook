import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { openDatabase } from "@/lib/db";
import type { GmailMessageSummary, GmailThreadRecord } from "@/lib/gmail";
import {
  applySendQueue,
  createIssueFromUnderstanding,
  importPreparedInboundBatch,
  prepareDraftBatch,
  prepareInboundBatch,
  renderAndSaveDrafts,
} from "@/lib/sync";

class FakeGmailAdapter {
  public sentReplies: Array<{ threadId: string; html: string }> = [];

  constructor(
    private readonly threads: GmailThreadRecord[],
    private readonly manualReplyThreadIds = new Set<string>(),
  ) {}

  async listLabeledThreads(): Promise<GmailThreadRecord[]> {
    return this.threads;
  }

  async hasHumanReplyAfter(threadId: string): Promise<boolean> {
    return this.manualReplyThreadIds.has(threadId);
  }

  async sendReply(input: { threadId: string; html: string }): Promise<GmailMessageSummary> {
    this.sentReplies.push(input);
    return {
      id: `sent-${input.threadId}`,
      threadId: input.threadId,
      subject: "reply",
      fromEmail: "agent@example.com",
      fromName: "Agent",
      htmlBody: input.html,
      textBody: input.html,
      internalDate: new Date("2026-05-30T12:00:00Z").toISOString(),
      direction: "outbound",
    };
  }
}

describe("sync workflow", () => {
  const root = mkdtempSync(path.join(os.tmpdir(), "customer-email-assist-"));
  const dbPath = path.join(root, "assist.sqlite3");
  const policyPath = path.join(root, "policy.md");

  beforeAll(() => {
    writeFileSync(
      policyPath,
      "Refunds are available within 30 days when the customer received the wrong item.\nBilling disputes should include the invoice number.\nPrivacy requests require manual review.",
      "utf8",
    );
  });

  afterAll(() => {
    rmSync(root, { recursive: true, force: true });
  });

  it("creates pending customers and issues from inbound Gmail threads", async () => {
    const db = openDatabase(dbPath);
    const gmail = new FakeGmailAdapter([
      {
        threadId: "thread-1",
        subject: "Refund request",
        messages: [
          {
            id: "msg-1",
            threadId: "thread-1",
            subject: "Refund request",
            fromEmail: "casey@example.com",
            fromName: "Casey",
            htmlBody: "<div>I received the wrong item and need a refund.</div>",
            textBody: "I received the wrong item and need a refund.",
            internalDate: "2026-05-29T12:00:00Z",
            direction: "inbound",
          },
        ],
      },
    ]);

    const batch = await prepareInboundBatch(db, gmail);

    expect(batch.items).toHaveLength(1);
    expect(batch.items[0]?.customer.status).toBe("pending");

    createIssueFromUnderstanding(db, {
      gmailThreadId: "thread-1",
      gmailLastInboundMessageId: "msg-1",
      customerEmail: "casey@example.com",
      customerName: "Casey",
      subject: "Refund request",
      receivedAt: "2026-05-29T12:00:00Z",
      originalMessageText: batch.items[0]!.cleanBody,
      classification: "refund_request",
      summary: "Customer reports the wrong item and requests a refund.",
      urgency: "normal",
      actionSuggestion: "send_reply",
    });

    const customer = db
      .prepare("SELECT status FROM customers WHERE email = ?")
      .get("casey@example.com") as { status: string };
    const issue = db
      .prepare("SELECT classification, issue_status FROM issues WHERE gmail_thread_id = ?")
      .get("thread-1") as { classification: string; issue_status: string };

    expect(customer.status).toBe("pending");
    expect(issue.classification).toBe("refund_request");
    expect(issue.issue_status).toBe("draft_ready");
  });

  it("imports prepared inbound items and creates issues without Gmail OAuth access", () => {
    const connectorDbPath = path.join(root, "connector-import.sqlite3");
    const db = openDatabase(connectorDbPath);

    const imported = importPreparedInboundBatch(db, [
      {
        gmailThreadId: "thread-import-1",
        gmailLastInboundMessageId: "msg-import-1",
        subject: "Invoice correction request",
        cleanBody: "Hi support, can you update the invoice before payment is sent?",
        receivedAt: "2026-05-30T08:15:00Z",
        customer: {
          email: "avery@example.com",
          displayName: "Avery",
          description: "",
          status: "pending",
        },
      },
    ]);

    expect(imported.issueIds).toHaveLength(1);
    const issue = db
      .prepare("SELECT classification, summary FROM issues WHERE gmail_thread_id = ?")
      .get("thread-import-1") as { classification: string; summary: string };

    expect(issue.classification).toBe("billing_issue");
    expect(issue.summary).toContain("Hi support");
  });

  it("renders policy-grounded drafts and auto-approves pending customers when sending is approved", async () => {
    const db = openDatabase(dbPath);

    const issue = db
      .prepare("SELECT id FROM issues WHERE gmail_thread_id = ?")
      .get("thread-1") as { id: number };

    const draftBatch = prepareDraftBatch(db, policyPath);
    expect(draftBatch.items[0]?.policyEvidence[0]).toContain("Refunds are available");

    renderAndSaveDrafts(db, [
      {
        issueId: issue.id,
        classification: "refund_request",
        draftFields: {
          customerName: "Casey",
          acknowledgement: "I understand the wrong item was delivered.",
          nextStep: "Please reply with your order number so we can process the request.",
          policyEvidence: draftBatch.items[0]!.policyEvidence,
          signoff: "Support Team",
        },
      },
    ]);

    db.prepare(
      "UPDATE issues SET issue_status = 'approved_to_send', approved_at = ? WHERE id = ?",
    ).run("2026-05-30T09:00:00Z", issue.id);

    const gmail = new FakeGmailAdapter([], new Set());
    const sendResult = await applySendQueue(db, gmail);

    expect(sendResult.sentCount).toBe(1);
    expect(gmail.sentReplies).toHaveLength(1);
    const customer = db
      .prepare("SELECT status FROM customers WHERE email = ?")
      .get("casey@example.com") as { status: string };
    expect(customer.status).toBe("approved");
  });

  it("marks issues resolved without sending when a human already replied in Gmail", async () => {
    const db = openDatabase(dbPath);
    db.prepare(
      "UPDATE issues SET issue_status = 'approved_to_send', approved_at = ?, resolved_at = NULL, sent_at = NULL WHERE gmail_thread_id = ?",
    ).run("2026-05-30T11:00:00Z", "thread-1");

    const gmail = new FakeGmailAdapter([], new Set(["thread-1"]));
    const sendResult = await applySendQueue(db, gmail);

    expect(sendResult.sentCount).toBe(0);
    expect(sendResult.manuallyResolvedCount).toBe(1);
    const issue = db
      .prepare("SELECT issue_status, resolved_at FROM issues WHERE gmail_thread_id = ?")
      .get("thread-1") as { issue_status: string; resolved_at: string | null };
    expect(issue.issue_status).toBe("resolved");
    expect(issue.resolved_at).not.toBeNull();
  });
});
