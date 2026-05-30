import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { updateIssue } from "@/lib/repository";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const body = (await request.json()) as {
    draftReplyHtml?: string;
    action?: "approve_to_send" | "mark_resolved" | "queue_send";
  };
  const db = openDatabase();
  if (body.action === "queue_send") {
    updateIssue(db, Number(id), {
      draftReplyHtml: body.draftReplyHtml,
      action: "approve_to_send",
    });
    return NextResponse.json({ ok: true, queued: true });
  }

  updateIssue(db, Number(id), {
    draftReplyHtml: body.draftReplyHtml,
    action: body.action,
  });
  return NextResponse.json({ ok: true });
}
