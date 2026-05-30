import { google } from "googleapis";

export interface GmailMessageSummary {
  id: string;
  threadId: string;
  subject: string;
  fromEmail: string;
  fromName: string;
  htmlBody: string;
  textBody: string;
  internalDate: string;
  direction: "inbound" | "outbound";
}

export interface GmailThreadRecord {
  threadId: string;
  subject: string;
  messages: GmailMessageSummary[];
}

export interface GmailAdapter {
  listLabeledThreads(): Promise<GmailThreadRecord[]>;
  hasHumanReplyAfter(threadId: string, lastInboundMessageId?: string): Promise<boolean>;
  sendReply(input: {
    threadId: string;
    html: string;
    text?: string;
    subject?: string;
    toEmail?: string;
  }): Promise<GmailMessageSummary>;
}

function getHeader(headers: Array<{ name?: string | null; value?: string | null }> | undefined, name: string): string {
  const header = headers?.find((entry) => entry.name?.toLowerCase() === name.toLowerCase());
  return header?.value ?? "";
}

function parseAddress(value: string): { email: string; name: string } {
  const match = value.match(/^(.*)<([^>]+)>$/);
  if (!match) {
    return { email: value.trim().toLowerCase(), name: value.trim() };
  }
  return {
    name: match[1]!.trim().replace(/^"|"$/g, ""),
    email: match[2]!.trim().toLowerCase(),
  };
}

function decodeBase64Url(input?: string | null): string {
  if (!input) {
    return "";
  }
  return Buffer.from(input.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8");
}

function extractBodies(payload: {
  body?: { data?: string | null };
  mimeType?: string | null;
  parts?: Array<{
    mimeType?: string | null;
    body?: { data?: string | null };
    parts?: unknown[];
  }>;
} | null | undefined): { htmlBody: string; textBody: string } {
  if (!payload) {
    return { htmlBody: "", textBody: "" };
  }

  const parts = payload.parts ?? [];
  let htmlBody = payload.mimeType === "text/html" ? decodeBase64Url(payload.body?.data) : "";
  let textBody = payload.mimeType === "text/plain" ? decodeBase64Url(payload.body?.data) : "";

  for (const part of parts) {
    if (part.mimeType === "text/html" && !htmlBody) {
      htmlBody = decodeBase64Url(part.body?.data);
    }
    if (part.mimeType === "text/plain" && !textBody) {
      textBody = decodeBase64Url(part.body?.data);
    }
  }

  return { htmlBody, textBody };
}

export class GoogleGmailAdapter implements GmailAdapter {
  private readonly gmail;
  private readonly operatorEmail: string;
  private readonly label: string;

  constructor() {
    const oauth2 = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      process.env.GOOGLE_REDIRECT_URI,
    );
    oauth2.setCredentials({
      refresh_token: process.env.GOOGLE_REFRESH_TOKEN,
    });
    this.gmail = google.gmail({ version: "v1", auth: oauth2 });
    this.operatorEmail = (process.env.CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL ?? "").toLowerCase();
    this.label = process.env.CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL ?? "";
  }

  async listLabeledThreads(): Promise<GmailThreadRecord[]> {
    if (!this.label) {
      return [];
    }
    const threadList = await this.gmail.users.threads.list({
      userId: "me",
      labelIds: [this.label],
      maxResults: 20,
    });

    const threads = threadList.data.threads ?? [];
    const results: GmailThreadRecord[] = [];
    for (const thread of threads) {
      if (!thread.id) {
        continue;
      }
      const full = await this.gmail.users.threads.get({
        userId: "me",
        id: thread.id,
        format: "full",
      });
      const messages = (full.data.messages ?? []).flatMap((message) => {
        if (!message.id || !message.threadId) {
          return [];
        }
        const headers = message.payload?.headers ?? [];
        const from = parseAddress(getHeader(headers, "From"));
        const { htmlBody, textBody } = extractBodies(message.payload);
        return [
          {
            id: message.id,
            threadId: message.threadId,
            subject: getHeader(headers, "Subject"),
            fromEmail: from.email,
            fromName: from.name,
            htmlBody,
            textBody,
            internalDate: message.internalDate
              ? new Date(Number(message.internalDate)).toISOString()
              : new Date().toISOString(),
            direction: this.operatorEmail && from.email === this.operatorEmail ? "outbound" : "inbound",
          } satisfies GmailMessageSummary,
        ];
      });

      if (messages.length === 0) {
        continue;
      }

      results.push({
        threadId: thread.id,
        subject: messages[messages.length - 1]!.subject,
        messages,
      });
    }
    return results;
  }

  async hasHumanReplyAfter(threadId: string, lastInboundMessageId?: string): Promise<boolean> {
    const thread = await this.gmail.users.threads.get({
      userId: "me",
      id: threadId,
      format: "full",
    });
    let foundLastInbound = !lastInboundMessageId;
    for (const message of thread.data.messages ?? []) {
      if (!message.id) {
        continue;
      }
      if (message.id === lastInboundMessageId) {
        foundLastInbound = true;
        continue;
      }
      if (!foundLastInbound) {
        continue;
      }
      const from = parseAddress(getHeader(message.payload?.headers ?? [], "From"));
      if (this.operatorEmail && from.email === this.operatorEmail) {
        return true;
      }
    }
    return false;
  }

  async sendReply(input: {
    threadId: string;
    html: string;
    text?: string;
    subject?: string;
    toEmail?: string;
  }): Promise<GmailMessageSummary> {
    const mime = [
      `To: ${input.toEmail ?? ""}`,
      `Subject: ${input.subject ?? "Re: Your support request"}`,
      "Content-Type: text/html; charset=UTF-8",
      "",
      input.html,
    ].join("\n");
    const raw = Buffer.from(mime)
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");

    const sent = await this.gmail.users.messages.send({
      userId: "me",
      requestBody: {
        raw,
        threadId: input.threadId,
      },
    });

    return {
      id: sent.data.id ?? "",
      threadId: sent.data.threadId ?? input.threadId,
      subject: input.subject ?? "Re: Your support request",
      fromEmail: this.operatorEmail,
      fromName: "Customer Email Assist",
      htmlBody: input.html,
      textBody: input.text ?? "",
      internalDate: new Date().toISOString(),
      direction: "outbound",
    };
  }
}
