import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { createCustomer, listCustomers } from "@/lib/repository";
import type { CustomerStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

export function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const db = openDatabase();
  const statuses = searchParams.getAll("status") as CustomerStatus[];
  return NextResponse.json(
    listCustomers(db, {
      page: Number(searchParams.get("page") ?? "1"),
      pageSize: Number(searchParams.get("pageSize") ?? "10"),
      search: searchParams.get("search") ?? undefined,
      statuses: statuses.length > 0 ? statuses : undefined,
    }),
  );
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as {
    email: string;
    displayName: string;
    description: string;
    status: CustomerStatus;
  };
  const db = openDatabase();
  const customer = createCustomer(db, body);
  return NextResponse.json(customer, { status: 201 });
}
