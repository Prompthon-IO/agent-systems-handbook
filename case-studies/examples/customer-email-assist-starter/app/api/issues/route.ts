import { NextRequest, NextResponse } from "next/server";

import { openDatabase } from "@/lib/db";
import { listIssues } from "@/lib/repository";
import type { IssueClassification } from "@/lib/types";

export const dynamic = "force-dynamic";

export function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const db = openDatabase();
  const classifications = searchParams.getAll("classification") as IssueClassification[];
  const response = listIssues(db, {
    page: Number(searchParams.get("page") ?? "1"),
    pageSize: Number(searchParams.get("pageSize") ?? "10"),
    search: searchParams.get("search") ?? undefined,
    classification: classifications.length > 0 ? classifications : undefined,
    issueStatus: (searchParams.get("issueStatus") as Parameters<typeof listIssues>[1]["issueStatus"]) ?? undefined,
    includeResolved: searchParams.get("includeResolved") === "true",
  });
  return NextResponse.json(response);
}
