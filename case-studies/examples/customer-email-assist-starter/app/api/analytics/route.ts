import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { getAnalytics } from "@/lib/repository";

export const dynamic = "force-dynamic";

export function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const db = openDatabase();
  return NextResponse.json(
    getAnalytics(db, {
      start: searchParams.get("start") ?? undefined,
      end: searchParams.get("end") ?? undefined,
    }),
  );
}
