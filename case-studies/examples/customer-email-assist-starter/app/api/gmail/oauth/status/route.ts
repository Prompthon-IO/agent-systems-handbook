import { NextResponse } from "next/server";

import { getGoogleOAuthStatus } from "@/lib/gmail-oauth";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(getGoogleOAuthStatus());
}
