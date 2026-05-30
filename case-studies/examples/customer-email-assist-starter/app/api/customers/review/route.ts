import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { listCustomerReviewQueue } from "@/lib/repository";

export const dynamic = "force-dynamic";

export function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const db = openDatabase();
  return NextResponse.json(
    listCustomerReviewQueue(db, {
      page: Number(searchParams.get("page") ?? "1"),
      pageSize: Number(searchParams.get("pageSize") ?? "10"),
      search: searchParams.get("search") ?? undefined,
    }),
  );
}
