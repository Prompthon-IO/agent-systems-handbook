import type Database from "better-sqlite3";

import type {
  ActionSuggestion,
  CustomerStatus,
  IssueClassification,
  IssueStatus,
  Urgency,
} from "@/lib/types";

function nowIso(): string {
  return new Date().toISOString();
}

function htmlToText(input: string): string {
  return input
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

type IssueRow = {
  id: number;
  customer_name: string;
  customer_email: string;
  classification: IssueClassification;
  summary: string;
  urgency: Urgency;
  action_suggestion: ActionSuggestion;
  issue_status: IssueStatus;
  received_at: string;
  original_message_text: string;
  draft_reply_html: string | null;
  draft_reply_text: string | null;
  draft_template_json: string | null;
  gmail_thread_id: string;
};

export interface IssueListParams {
  page: number;
  pageSize: number;
  search?: string;
  classification?: IssueClassification[];
  issueStatus?: IssueStatus;
  includeResolved?: boolean;
}

export interface CustomerListParams {
  page: number;
  pageSize: number;
  search?: string;
  statuses?: CustomerStatus[];
}

export interface CustomerInput {
  email: string;
  displayName: string;
  description: string;
  status: CustomerStatus;
}

export interface IssueRecordInput {
  gmailThreadId: string;
  gmailLastInboundMessageId: string;
  customerId: number;
  receivedAt: string;
  classification: IssueClassification;
  summary: string;
  urgency: Urgency;
  originalMessageText: string;
  actionSuggestion: ActionSuggestion;
  issueStatus: IssueStatus;
}

function buildIssueWhere(params: IssueListParams) {
  const clauses: string[] = [];
  const values: unknown[] = [];

  if (params.search) {
    clauses.push(
      "(customers.display_name LIKE ? OR customers.email LIKE ? OR issues.summary LIKE ? OR issues.original_message_text LIKE ?)",
    );
    const needle = `%${params.search}%`;
    values.push(needle, needle, needle, needle);
  }
  if (params.classification && params.classification.length > 0) {
    clauses.push(
      `issues.classification IN (${params.classification.map(() => "?").join(", ")})`,
    );
    values.push(...params.classification);
  }
  if (params.issueStatus) {
    clauses.push("issues.issue_status = ?");
    values.push(params.issueStatus);
  }
  if (!params.includeResolved) {
    clauses.push("issues.issue_status != 'resolved'");
  }

  return {
    whereSql: clauses.length > 0 ? `WHERE ${clauses.join(" AND ")}` : "",
    values,
  };
}

function parsePolicyEvidence(draftTemplateJson: string | null): string[] {
  if (!draftTemplateJson) {
    return [];
  }
  try {
    const parsed = JSON.parse(draftTemplateJson) as { policyEvidence?: string[] };
    return Array.isArray(parsed.policyEvidence) ? parsed.policyEvidence : [];
  } catch {
    return [];
  }
}

function normalizeIssueRow(row: IssueRow) {
  return {
    id: row.id,
    customerName: row.customer_name,
    customerEmail: row.customer_email,
    classification: row.classification,
    summary: row.summary,
    urgency: row.urgency,
    actionSuggestion: row.action_suggestion,
    issueStatus: row.issue_status,
    receivedAt: row.received_at,
    originalMessageText: row.original_message_text,
    draftReplyHtml: row.draft_reply_html,
    draftReplyText: row.draft_reply_text,
    policyEvidence: parsePolicyEvidence(row.draft_template_json),
    gmailThreadId: row.gmail_thread_id,
  };
}

export function createCustomer(db: Database.Database, input: CustomerInput) {
  const timestamp = nowIso();
  const inserted = db
    .prepare(
      `
        INSERT INTO customers (email, display_name, description, status, created_at, updated_at, last_seen_at)
        VALUES (@email, @displayName, @description, @status, @timestamp, @timestamp, @timestamp)
      `,
    )
    .run({
      ...input,
      timestamp,
    });

  return {
    id: Number(inserted.lastInsertRowid),
    ...input,
  };
}

export function updateCustomer(
  db: Database.Database,
  id: number,
  input: Partial<CustomerInput>,
): void {
  const existing = db
    .prepare("SELECT email, display_name, description, status FROM customers WHERE id = ?")
    .get(id) as
    | {
        email: string;
        display_name: string;
        description: string;
        status: CustomerStatus;
      }
    | undefined;
  if (!existing) {
    throw new Error(`Customer ${id} not found.`);
  }

  db.prepare(
    `
      UPDATE customers
      SET email = @email,
          display_name = @displayName,
          description = @description,
          status = @status,
          updated_at = @timestamp
      WHERE id = @id
    `,
  ).run({
    id,
    email: input.email ?? existing.email,
    displayName: input.displayName ?? existing.display_name,
    description: input.description ?? existing.description,
    status: input.status ?? existing.status,
    timestamp: nowIso(),
  });
}

export function deleteCustomer(db: Database.Database, id: number): void {
  db.prepare("DELETE FROM customers WHERE id = ?").run(id);
}

export function listCustomers(db: Database.Database, params: CustomerListParams) {
  const clauses: string[] = [];
  const values: unknown[] = [];
  if (params.search) {
    clauses.push("(email LIKE ? OR display_name LIKE ? OR description LIKE ?)");
    const needle = `%${params.search}%`;
    values.push(needle, needle, needle);
  }
  if (params.statuses && params.statuses.length > 0) {
    clauses.push(`status IN (${params.statuses.map(() => "?").join(", ")})`);
    values.push(...params.statuses);
  }
  const whereSql = clauses.length > 0 ? `WHERE ${clauses.join(" AND ")}` : "";
  const offset = (params.page - 1) * params.pageSize;

  const items = db
    .prepare(
      `
        SELECT
          customers.id,
          customers.email,
          customers.display_name,
          customers.description,
          customers.status,
          customers.last_seen_at,
          COUNT(issues.id) AS issue_count
        FROM customers
        LEFT JOIN issues ON issues.customer_id = customers.id
        ${whereSql}
        GROUP BY customers.id
        ORDER BY customers.updated_at DESC
        LIMIT ? OFFSET ?
      `,
    )
    .all(...values, params.pageSize, offset)
    .map((row) => ({
      id: Number((row as { id: number }).id),
      email: (row as { email: string }).email,
      displayName: (row as { display_name: string }).display_name,
      description: (row as { description: string }).description,
      status: (row as { status: CustomerStatus }).status,
      lastSeenAt: (row as { last_seen_at: string | null }).last_seen_at,
      issueCount: Number((row as { issue_count: number }).issue_count),
    }));

  const total = Number(
    (
      db
        .prepare(`SELECT COUNT(*) AS count FROM customers ${whereSql}`)
        .get(...values) as { count: number }
    ).count,
  );

  return {
    items,
    total,
    page: params.page,
    pageSize: params.pageSize,
  };
}

export function listCustomerReviewQueue(db: Database.Database, params: CustomerListParams) {
  return listCustomers(db, {
    ...params,
    statuses: ["pending"],
  });
}

export function reviewCustomer(
  db: Database.Database,
  id: number,
  input: { status: "approved" | "ignored"; description?: string },
): void {
  updateCustomer(db, id, {
    status: input.status,
    description: input.description,
  });
}

export function upsertIssueRecord(db: Database.Database, input: IssueRecordInput) {
  const existing = db
    .prepare("SELECT id FROM issues WHERE gmail_thread_id = ?")
    .get(input.gmailThreadId) as { id: number } | undefined;
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
            issue_status = @issueStatus,
            gmail_last_inbound_message_id = @gmailLastInboundMessageId,
            last_synced_at = @timestamp,
            error_message = NULL
        WHERE id = @id
      `,
    ).run({
      ...input,
      id: existing.id,
      timestamp,
    });
    return existing.id;
  }

  const inserted = db
    .prepare(
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
          @issueStatus,
          @gmailLastInboundMessageId,
          @timestamp
        )
      `,
    )
    .run({
      ...input,
      timestamp,
    });
  return Number(inserted.lastInsertRowid);
}

export function listIssues(db: Database.Database, params: IssueListParams) {
  const { whereSql, values } = buildIssueWhere(params);
  const offset = (params.page - 1) * params.pageSize;
  const items = db
    .prepare(
      `
        SELECT
          issues.id,
          customers.display_name AS customer_name,
          customers.email AS customer_email,
          issues.classification,
          issues.summary,
          issues.urgency,
          issues.action_suggestion,
          issues.issue_status,
          issues.received_at,
          issues.original_message_text,
          issues.draft_reply_html,
          issues.draft_reply_text,
          issues.draft_template_json,
          issues.gmail_thread_id
        FROM issues
        JOIN customers ON customers.id = issues.customer_id
        ${whereSql}
        ORDER BY issues.received_at DESC
        LIMIT ? OFFSET ?
      `,
    )
    .all(...values, params.pageSize, offset)
    .map((row) => normalizeIssueRow(row as IssueRow));

  const total = Number(
    (
      db
        .prepare(
          `
            SELECT COUNT(*) AS count
            FROM issues
            JOIN customers ON customers.id = issues.customer_id
            ${whereSql}
          `,
        )
        .get(...values) as { count: number }
    ).count,
  );

  const countsRows = db
    .prepare(
      `
        SELECT issue_status, COUNT(*) AS count
        FROM issues
        GROUP BY issue_status
      `,
    )
    .all() as Array<{ issue_status: IssueStatus; count: number }>;

  const summaryCounts = {
    total: 0,
    draft_ready: 0,
    approved_to_send: 0,
    resolved: 0,
    sync_error: 0,
  };
  for (const row of countsRows) {
    summaryCounts[row.issue_status] = Number(row.count);
    summaryCounts.total += Number(row.count);
  }

  return {
    items,
    total,
    page: params.page,
    pageSize: params.pageSize,
    summaryCounts,
  };
}

export function updateIssue(
  db: Database.Database,
  id: number,
  input: {
    draftReplyHtml?: string;
    action?: "approve_to_send" | "mark_resolved" | "revoke_send_approval";
  },
): void {
  const existing = db
    .prepare(
      `
        SELECT issues.customer_id, customers.status
        FROM issues
        JOIN customers ON customers.id = issues.customer_id
        WHERE issues.id = ?
      `,
    )
    .get(id) as { customer_id: number; status: CustomerStatus } | undefined;
  if (!existing) {
    throw new Error(`Issue ${id} not found.`);
  }

  const timestamp = nowIso();
  if (input.draftReplyHtml !== undefined) {
    db.prepare(
      `
        UPDATE issues
        SET draft_reply_html = ?,
            draft_reply_text = ?,
            last_synced_at = ?
        WHERE id = ?
      `,
    ).run(input.draftReplyHtml, htmlToText(input.draftReplyHtml), timestamp, id);
  }

  if (input.action === "approve_to_send") {
    db.prepare(
      `
        UPDATE issues
        SET issue_status = 'approved_to_send',
            approved_at = ?,
            last_synced_at = ?
        WHERE id = ?
      `,
    ).run(timestamp, timestamp, id);
    if (existing.status === "pending") {
      db.prepare(
        `
          UPDATE customers
          SET status = 'approved',
              updated_at = ?,
              last_seen_at = ?
          WHERE id = ?
        `,
      ).run(timestamp, timestamp, existing.customer_id);
    }
  }

  if (input.action === "revoke_send_approval") {
    db.prepare(
      `
        UPDATE issues
        SET issue_status = 'draft_ready',
            approved_at = NULL,
            last_synced_at = ?
        WHERE id = ?
      `,
    ).run(timestamp, id);
  }

  if (input.action === "mark_resolved") {
    db.prepare(
      `
        UPDATE issues
        SET issue_status = 'resolved',
            resolved_at = ?,
            last_synced_at = ?
        WHERE id = ?
      `,
    ).run(timestamp, timestamp, id);
  }
}

export function getAnalytics(
  db: Database.Database,
  input: { start?: string; end?: string },
) {
  const start = input.start ?? "1970-01-01T00:00:00.000Z";
  const end = input.end ?? "2999-12-31T23:59:59.999Z";

  const typeCounts = db
    .prepare(
      `
        SELECT classification, COUNT(*) AS count
        FROM issues
        WHERE received_at BETWEEN ? AND ?
        GROUP BY classification
      `,
    )
    .all(start, end);

  const statusCounts = db
    .prepare(
      `
        SELECT issue_status, COUNT(*) AS count
        FROM issues
        WHERE received_at BETWEEN ? AND ?
        GROUP BY issue_status
      `,
    )
    .all(start, end);

  const dailyRows = db
    .prepare(
      `
        SELECT
          substr(received_at, 1, 10) AS day,
          classification,
          issue_status,
          COUNT(*) AS count
        FROM issues
        WHERE received_at BETWEEN ? AND ?
        GROUP BY day, classification, issue_status
        ORDER BY day ASC
      `,
    )
    .all(start, end) as Array<{
    day: string;
    classification: IssueClassification;
    issue_status: IssueStatus;
    count: number;
  }>;

  return {
    typeCounts: typeCounts.map((row) => ({
      classification: (row as { classification: IssueClassification }).classification,
      count: Number((row as { count: number }).count),
    })),
    statusCounts: statusCounts.map((row) => ({
      issueStatus: (row as { issue_status: IssueStatus }).issue_status,
      count: Number((row as { count: number }).count),
    })),
    buckets: dailyRows.map((row) => ({
      day: row.day,
      classification: row.classification,
      issueStatus: row.issue_status,
      count: Number(row.count),
    })),
  };
}
