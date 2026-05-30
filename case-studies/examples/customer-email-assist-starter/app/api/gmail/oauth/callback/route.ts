import { NextRequest, NextResponse } from "next/server";

import { persistGoogleOAuthCode } from "@/lib/gmail-oauth";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const origin = request.nextUrl.origin;
  const state = request.nextUrl.searchParams.get("state");
  const expectedState = request.cookies.get("customer_email_assist_oauth_state")?.value;
  const code = request.nextUrl.searchParams.get("code");
  const error = request.nextUrl.searchParams.get("error");

  if (error) {
    return NextResponse.redirect(new URL(`/?gmail_oauth=${encodeURIComponent(error)}`, origin));
  }

  if (!state || !expectedState || state !== expectedState || !code) {
    return NextResponse.redirect(new URL("/?gmail_oauth=invalid_state", origin));
  }

  try {
    const result = await persistGoogleOAuthCode({ code, origin });
    const status = result.hasRefreshToken ? "connected" : "missing_refresh_token";
    const response = NextResponse.redirect(new URL(`/?gmail_oauth=${status}`, origin));
    response.cookies.delete("customer_email_assist_oauth_state");
    return response;
  } catch {
    return NextResponse.redirect(new URL("/?gmail_oauth=exchange_failed", origin));
  }
}
