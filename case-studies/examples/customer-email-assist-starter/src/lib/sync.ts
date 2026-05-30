import type Database from "better-sqlite3";

import {
  cleanEmailBody,
  classifyHeuristically,
  selectActionSuggestion,
  summarizeCleanBody,
} from "@/lib/email-processing";
import type { GmailAdapter, GmailThreadRecord } from "@/lib/gmail";
import { findPolicyEvidence, loadPolicyText } from "@/lib/policy";
import { renderDraftFromTemplate } from "@/lib/draft-templates";
import type {
  DraftBatchItem,
  DraftRenderRecord,
  IssueClassification,
  PreparedInboundItem,
  UnderstandingRecord,
} from "@/lib/types";

function nowIso(): string {
  return new Date().toISOString();
}

function latestInboundMessage(thread: GmailThreadRecord) {
  const inbound = thread.messages
    .filter((message) => message.direction === "inbound")
    .sort((left, right) => left.internalDate.localeCompare(right.internalDate));
  return inbound[inbound.length - 1] ?? null;
}

function upsertCustomer(
  db: Database.Database,
  input: {
    email: string;
    displayName: string;
    status?: "pending" | "approved" | "ignored";
    description?: string;
  },
): { id: number; status: "pending" | "approved" | "ignored" } {
  const timestamp = nowIso();
  db.prepare(
    `
      INSERT INTO customers (email, display_name, description, status, created_at, updated_at, last_seen_at)
      VALUES (@email, @displayName, @description, @status, @timestamp, @timestamp, @timestamp)
      ON CONFLICT(email) DO UPDATE SET
        display_name = excluded.display_name,
        updated_at = excluded.updated_at,
        last_seen_at = excluded.last_seen_at
    `,
  ).run({
    email: input.email,
    displayName: input.displayName,
    description: input.description ?? "",
    status: input.status ?? "pending",
    timestamp,
  });

  return db
    .prepare("SELECT id, status FROM customers WHERE email = ?")
    .get(input.email) as { id: number; status: "pending" | "approved" | "ignored" };
}

export async function prepareInboundBatch(
  db: Database.Database,
  gmail: Pick<GmailAdapter, "listLabeledThreads">,
  limit = 4,
): Promise<{ items: PreparedInboundItem[] }> {
  const threads = await gmail.listLabeledThreads();
  const items: PreparedInboundItem[] = [];

  for (const thread of threads) {
    if (items.length >= limit) {
      break;
    }
    const inbound = latestInboundMessage(thread);
    if (!inbound) {
      continue;
    }

    const knownCustomer = db
      .prepare("SELECT status, description FROM customers WHERE email = ?")
      .get(inbound.fromEmail) as { status: "pending" | "approved" | "ignored"; description: string } | undefined;
    if (knownCustomer?.status === "ignored") {
      continue;
    }

    const cleanBody = cleanEmailBody(inbound.htmlBody || inbound.textBody);
    items.push({
      gmailThreadId: thread.threadId,
      gmailLastInboundMessageId: inbound.id,
      subject: inbound.subject,
      cleanBody,
      receivedAt: inbound.internalDate,
      customer: {
        email: inbound.fromEmail,
        displayName: inbound.fromName,
        description: knownCustomer?.description ?? "",
        status: knownCustomer?.status ?? "pending",
      },
    });
  }

  return { items };
}

export function createIssueFromUnderstanding(
  db: Database.Database,
  record: UnderstandingRecord,
): { issueId: number } {
  const customer = upsertCustomer(db, {
    email: record.customerEmail,
    displayName: record.customerName,
    status: "pending",
  });

  const existing = db
    .prepare("SELECT id FROM issues WHERE gmail_thread_id = ?")
    .get(record.gmailThreadId) as { id: number } | undefined;

  const timestamp = nowIso();
  if (existing) {
    db.prepare(
      `
        UPDATE issues
        SET customer_id = @customerId,
            received_at = @receivedAt,
            classification = @classification,
            summary = @summary,
            urgency = @urgency,
            original_message_text = @originalMessageText,
            action_suggestion = @actionSuggestion,
            issue_status = 'draft_ready',
            resolved_at = NULL,
            approved_at = NULL,
            sent_at = NULL,
            gmail_last_inbound_message_id = @gmailLastInboundMessageId,
            last_synced_at = @lastSyncedAt,
            error_message = NULL
        WHERE id = @issueId
      `,
    ).run({
      issueId: existing.id,
      customerId: customer.id,
      receivedAt: record.receivedAt,
      classification: record.classification,
      summary: record.summary,
      urgency: record.urgency,
      originalMessageText: record.originalMessageText,
      actionSuggestion: record.actionSuggestion,
      gmailLastInboundMessageId: record.gmailLastInboundMessageId,
      lastSyncedAt: timestamp,
    });
    return { issueId: existing.id };
  }

  const inserted = db.prepare(
    `
      INSERT INTO issues (
        customer_id,
        gmail_thread_id,
        received_at,
        classification,
        summary,
        urgency,
        original_message_text,
        action_suggestion,
        issue_status,
        gmail_last_inbound_message_id,
        last_synced_at
      ) VALUES (
        @customerId,
        @gmailThreadId,
        @receivedAt,
        @classification,
        @summary,
        @urgency,
        @originalMessageText,
        @actionSuggestion,
        'draft_ready',
        @gmailLastInboundMessageId,
        @lastSyncedAt
      )
    `,
  ).run({
    customerId: customer.id,
    gmailThreadId: record.gmailThreadId,
    receivedAt: record.receivedAt,
    classification: record.classification,
    summary: record.summary,
    urgency: record.urgency,
    originalMessageText: record.originalMessageText,
    actionSuggestion: record.actionSuggestion,
    gmailLastInboundMessageId: record.gmailLastInboundMessageId,
    lastSyncedAt: timestamp,
  });

  return { issueId: Number(inserted.lastInsertRowid) };
}

export function createUnderstandingFromPreparedItem(item: PreparedInboundItem): UnderstandingRecord {
  const heuristic = classifyHeuristically(`${item.subject}\n${item.cleanBody}`);
  return {
    gmailThreadId: item.gmailThreadId,
    gmailLastInboundMessageId: item.gmailLastInboundMessageId,
    customerEmail: item.customer.email,
    customerName: item.customer.displayName,
    subject: item.subject,
    receivedAt: item.receivedAt,
    originalMessageText: item.cleanBody,
    classification: heuristic.classification,
    summary: summarizeCleanBody(item.cleanBody),
    urgency: heuristic.urgency,
    actionSuggestion: selectActionSuggestion(heuristic.classification),
  };
}

export function importPreparedInboundBatch(
  db: Database.Database,
  items: PreparedInboundItem[],
): { issueIds: number[] } {
  const issueIds: number[] = [];
  for (const item of items) {
    const understanding = createUnderstandingFromPreparedItem(item);
    issueIds.push(createIssueFromUnderstanding(db, understanding).issueId);
  }
  return { issueIds };
}

export function prepareDraftBatch(
  db: Database.Database,
  policyPath?: string,
): { items: DraftBatchItem[] } {
  const policyText = loadPolicyText(policyPath);
  const rows = db
    .prepare(
      `
        SELECT
          issues.id,
          issues.classification,
          issues.summary,
          issues.original_message_text,
          customers.display_name
        FROM issues
        JOIN customers ON customers.id = issues.customer_id
        WHERE issues.issue_status = 'draft_ready'
        ORDER BY issues.received_at DESC
      `,
    )
    .all() as Array<{
    id: number;
    classification: IssueClassification;
    summary: string;
    original_message_text: string;
    display_name: string;
  }>;

  return {
    items: rows.map((row) => ({
      issueId: row.id,
      classification: row.classification,
      customerName: row.display_name,
      summary: row.summary,
      originalMessageText: row.original_message_text,
      policyEvidence: findPolicyEvidence(policyText, row.classification),
    })),
  };
}

export function renderAndSaveDrafts(
  db: Database.Database,
  records: DraftRenderRecord[],
): void {
  const statement = db.prepare(
    `
      UPDATE issues
      SET draft_template_json = @draftTemplateJson,
          draft_reply_html = @draftReplyHtml,
          draft_reply_text = @draftReplyText,
          last_synced_at = @lastSyncedAt
      WHERE id = @issueId
    `,
  );

  for (const record of records) {
    const draft = renderDraftFromTemplate({
      classification: record.classification,
      ...record.draftFields,
    });
    statement.run({
      issueId: record.issueId,
      draftTemplateJson: JSON.stringify(record.draftFields),
      draftReplyHtml: draft.html,
      draftReplyText: draft.text,
      lastSyncedAt: nowIso(),
    });
  }
}

async function sendIssueRow(
  db: Database.Database,
  gmail: Pick<GmailAdapter, "hasHumanReplyAfter" | "sendReply">,
  row: {
    id: number;
    gmail_thread_id: string;
    gmail_last_inbound_message_id: string;
    draft_reply_html: string | null;
    draft_reply_text: string | null;
    email: string;
    status: "pending" | "approved" | "ignored";
  },
): Promise<"sent" | "manually_resolved" | "error"> {
  const timestamp = nowIso();
  if (await gmail.hasHumanReplyAfter(row.gmail_thread_id, row.gmail_last_inbound_message_id)) {
    db.prepare(
      `
        UPDATE issues
        SET issue_status = 'resolved',
            resolved_at = ?,
            last_synced_at = ?
        WHERE id = ?
      `,
    ).run(timestamp, timestamp, row.id);
    return "manually_resolved";
  }

  if (!row.draft_reply_html) {
    db.prepare(
      `
        UPDATE issues
        SET issue_status = 'sync_error',
            error_message = ?,
            last_synced_at = ?
        WHERE id = ?
      `,
    ).run("Approved issue is missing a rendered draft.", timestamp, row.id);
    return "error";
  }

  try {
    const sent = await gmail.sendReply({
      threadId: row.gmail_thread_id,
      html: row.draft_reply_html,
      text: row.draft_reply_text ?? undefined,
      toEmail: row.email,
    });
    db.prepare(
      `
        UPDATE issues
        SET issue_status = 'resolved',
            sent_at = ?,
            resolved_at = ?,
            gmail_last_outbound_message_id = ?,
            last_synced_at = ?,
            error_message = NULL
        WHERE id = ?
      `,
    ).run(timestamp, timestamp, sent.id, timestamp, row.id);
    if (row.status === "pending") {
      db.prepare(
        `
          UPDATE customers
          SET status = 'approved',
              updated_at = ?,
              last_seen_at = ?
          WHERE email = ?
        `,
      ).run(timestamp, timestamp, row.email);
    }
    return "sent";
  } catch (error) {
    db.prepare(
      `
        UPDATE issues
        SET issue_status = 'sync_error',
            error_message = ?,
            last_synced_at = ?
        WHERE id = ?
      `,
    ).run(error instanceof Error ? error.message : "Unknown send failure", timestamp, row.id);
    return "error";
  }
}

export async function sendIssueNow(
  db: Database.Database,
  gmail: Pick<GmailAdapter, "hasHumanReplyAfter" | "sendReply">,
  issueId: number,
): Promise<{ sent: boolean; manuallyResolved: boolean }> {
  const row = db
    .prepare(
      `
        SELECT
          issues.id,
          issues.gmail_thread_id,
          issues.gmail_last_inbound_message_id,
          issues.draft_reply_html,
          issues.draft_reply_text,
          customers.email,
          customers.status
        FROM issues
        JOIN customers ON customers.id = issues.customer_id
        WHERE issues.id = ?
      `,
    )
    .get(issueId) as
    | {
        id: number;
        gmail_thread_id: string;
        gmail_last_inbound_message_id: string;
        draft_reply_html: string | null;
        draft_reply_text: string | null;
        email: string;
        status: "pending" | "approved" | "ignored";
      }
    | undefined;

  if (!row) {
    throw new Error(`Issue ${issueId} not found.`);
  }

  const result = await sendIssueRow(db, gmail, row);
  return {
    sent: result === "sent",
    manuallyResolved: result === "manually_resolved",
  };
}

export async function applySendQueue(
  db: Database.Database,
  gmail: Pick<GmailAdapter, "hasHumanReplyAfter" | "sendReply">,
): Promise<{ sentCount: number; manuallyResolvedCount: number; errorCount: number }> {
  const rows = db
    .prepare(
      `
        SELECT
          issues.id,
          issues.gmail_thread_id,
          issues.gmail_last_inbound_message_id,
          issues.draft_reply_html,
          issues.draft_reply_text,
          customers.email,
          customers.status
        FROM issues
        JOIN customers ON customers.id = issues.customer_id
        WHERE issues.issue_status = 'approved_to_send'
        ORDER BY issues.approved_at ASC
      `,
    )
    .all() as Array<{
    id: number;
    gmail_thread_id: string;
    gmail_last_inbound_message_id: string;
    draft_reply_html: string | null;
    draft_reply_text: string | null;
    email: string;
    status: "pending" | "approved" | "ignored";
  }>;

  let sentCount = 0;
  let manuallyResolvedCount = 0;
  let errorCount = 0;

  for (const row of rows) {
    const result = await sendIssueRow(db, gmail, row);
    if (result === "manually_resolved") {
      manuallyResolvedCount += 1;
      continue;
    }
    if (result === "error") {
      errorCount += 1;
      continue;
    }
    sentCount += 1;
  }

  return { sentCount, manuallyResolvedCount, errorCount };
}
