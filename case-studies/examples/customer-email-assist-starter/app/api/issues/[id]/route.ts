import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { updateIssue } from "@/lib/repository";
import { GoogleGmailAdapter } from "@/lib/gmail";
import { sendIssueNow } from "@/lib/sync";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const body = (await request.json()) as {
    draftReplyHtml?: string;
    action?: "approve_to_send" | "mark_resolved" | "send_now";
  };
  const db = openDatabase();
  if (body.action === "send_now") {
    updateIssue(db, Number(id), {
      draftReplyHtml: body.draftReplyHtml,
      action: "approve_to_send",
    });
    const gmail = new GoogleGmailAdapter();
    await sendIssueNow(db, gmail, Number(id));
    return NextResponse.json({ ok: true, sent: true });
  }

  updateIssue(db, Number(id), {
    draftReplyHtml: body.draftReplyHtml,
    action: body.action,
  });
  return NextResponse.json({ ok: true });
}
