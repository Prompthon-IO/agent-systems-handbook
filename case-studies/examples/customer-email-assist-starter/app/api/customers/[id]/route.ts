import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { deleteCustomer, updateCustomer } from "@/lib/repository";
import type { CustomerStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const body = (await request.json()) as {
    email?: string;
    displayName?: string;
    description?: string;
    status?: CustomerStatus;
  };
  const db = openDatabase();
  updateCustomer(db, Number(id), body);
  return NextResponse.json({ ok: true });
}

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const db = openDatabase();
  deleteCustomer(db, Number(id));
  return NextResponse.json({ ok: true });
}
