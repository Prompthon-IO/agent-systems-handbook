import { google } from "googleapis";

import {
  readStoredGmailOAuth,
  resolveStoredRefreshToken,
  writeStoredGmailOAuth,
} from "@/lib/gmail-oauth-store";

export const GMAIL_OAUTH_SCOPES = [
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.readonly",
];

export function hasGoogleOAuthClientConfig(): boolean {
  return Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
}

export function hasGoogleOAuthSendConfig(): boolean {
  return hasGoogleOAuthClientConfig() && Boolean(resolveStoredRefreshToken());
}

export function resolveGoogleOAuthRedirectUri(origin: string): string {
  return process.env.GOOGLE_REDIRECT_URI || `${origin}/api/gmail/oauth/callback`;
}

export function createGoogleOAuthClient(redirectUri: string) {
  return new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    redirectUri,
  );
}

export function getGoogleOAuthStatus() {
  const stored = readStoredGmailOAuth();
  return {
    configured: hasGoogleOAuthClientConfig(),
    connected: Boolean(resolveStoredRefreshToken()),
    emailAddress:
      process.env.CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL ||
      stored?.emailAddress ||
      "",
    connectedAt: stored?.connectedAt ?? null,
    usesEnvRefreshToken: Boolean(process.env.GOOGLE_REFRESH_TOKEN),
  };
}

export async function persistGoogleOAuthCode(input: {
  code: string;
  origin: string;
}): Promise<{ emailAddress: string; hasRefreshToken: boolean }> {
  const redirectUri = resolveGoogleOAuthRedirectUri(input.origin);
  const oauth2 = createGoogleOAuthClient(redirectUri);
  const { tokens } = await oauth2.getToken(input.code);
  oauth2.setCredentials(tokens);

  const gmail = google.gmail({ version: "v1", auth: oauth2 });
  const profile = await gmail.users.getProfile({ userId: "me" });
  const emailAddress = profile.data.emailAddress ?? "";
  const refreshToken = tokens.refresh_token || readStoredGmailOAuth()?.refreshToken;

  if (!refreshToken) {
    return {
      emailAddress,
      hasRefreshToken: false,
    };
  }

  writeStoredGmailOAuth({
    connectedAt: new Date().toISOString(),
    emailAddress,
    refreshToken,
  });

  return {
    emailAddress,
    hasRefreshToken: true,
  };
}
