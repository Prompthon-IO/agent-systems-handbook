import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { reviewCustomer } from "@/lib/repository";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const body = (await request.json()) as {
    status: "approved" | "ignored";
    description?: string;
  };
  const db = openDatabase();
  reviewCustomer(db, Number(id), body);
  return NextResponse.json({ ok: true });
}
