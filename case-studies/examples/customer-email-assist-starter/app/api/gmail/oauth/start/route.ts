import { randomBytes } from "node:crypto";

import { NextRequest, NextResponse } from "next/server";

import {
  createGoogleOAuthClient,
  GMAIL_OAUTH_SCOPES,
  hasGoogleOAuthClientConfig,
  resolveGoogleOAuthRedirectUri,
} from "@/lib/gmail-oauth";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const origin = request.nextUrl.origin;
  if (!hasGoogleOAuthClientConfig()) {
    return NextResponse.redirect(new URL("/?gmail_oauth=missing_config", origin));
  }

  const state = randomBytes(16).toString("hex");
  const oauth2 = createGoogleOAuthClient(resolveGoogleOAuthRedirectUri(origin));
  const target = oauth2.generateAuthUrl({
    access_type: "offline",
    include_granted_scopes: true,
    prompt: "consent",
    scope: GMAIL_OAUTH_SCOPES,
    state,
  });
  const response = NextResponse.redirect(target);
  response.cookies.set("customer_email_assist_oauth_state", state, {
    httpOnly: true,
    maxAge: 10 * 60,
    path: "/",
    sameSite: "lax",
  });
  return response;
}
