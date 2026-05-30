import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { GoogleGmailAdapter } from "@/lib/gmail";
import { hasGoogleOAuthSendConfig } from "@/lib/gmail-oauth";
import { updateIssue } from "@/lib/repository";
import { sendIssueNow } from "@/lib/sync";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const body = (await request.json()) as {
    draftReplyHtml?: string;
    action?:
      | "approve_to_send"
      | "mark_resolved"
      | "queue_send"
      | "send_approved"
      | "revoke_send_approval";
  };
  const db = openDatabase();
  if (body.action === "queue_send") {
    updateIssue(db, Number(id), {
      draftReplyHtml: body.draftReplyHtml,
      action: "approve_to_send",
    });
    return NextResponse.json({ ok: true, queued: true });
  }

  if (body.action === "send_approved") {
    updateIssue(db, Number(id), {
      draftReplyHtml: body.draftReplyHtml,
      action: "approve_to_send",
    });
    if (!hasGoogleOAuthSendConfig()) {
      return NextResponse.json({
        ok: true,
        queued: true,
        sendMode: "connector_required",
      });
    }
    const result = await sendIssueNow(db, new GoogleGmailAdapter(), Number(id));
    return NextResponse.json({
      ok: result.sent || result.manuallyResolved,
      ...result,
    });
  }

  updateIssue(db, Number(id), {
    draftReplyHtml: body.draftReplyHtml,
    action: body.action,
  });
  return NextResponse.json({ ok: true });
}
