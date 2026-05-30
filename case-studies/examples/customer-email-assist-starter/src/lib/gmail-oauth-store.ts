import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export type StoredGmailOAuth = {
  connectedAt: string;
  emailAddress: string;
  refreshToken: string;
};

const DEFAULT_STATE_DIR = path.join(
  os.homedir(),
  ".codex",
  "state",
  "customer-email-assist",
);

function resolveStorePath(): string {
  return path.join(DEFAULT_STATE_DIR, "gmail-oauth.json");
}

export function readStoredGmailOAuth(): StoredGmailOAuth | null {
  const storePath = resolveStorePath();
  if (!fs.existsSync(storePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(storePath, "utf8")) as StoredGmailOAuth;
  } catch {
    return null;
  }
}

export function writeStoredGmailOAuth(input: StoredGmailOAuth): void {
  const storePath = resolveStorePath();
  fs.mkdirSync(path.dirname(storePath), { recursive: true, mode: 0o700 });
  fs.writeFileSync(storePath, `${JSON.stringify(input, null, 2)}\n`, { mode: 0o600 });
}

export function resolveStoredRefreshToken(): string | undefined {
  return process.env.GOOGLE_REFRESH_TOKEN || readStoredGmailOAuth()?.refreshToken;
}

export function resolveStoredOperatorEmail(): string {
  return (
    process.env.CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL ||
    readStoredGmailOAuth()?.emailAddress ||
    ""
  ).toLowerCase();
}
