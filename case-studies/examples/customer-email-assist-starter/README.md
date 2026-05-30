# Customer Email Assist Starter

This starter can run in two Gmail modes:

- Connector mode: Codex reads/sends through the Codex Gmail connector. This is easiest inside Codex, but the Next.js dashboard cannot call the connector directly.
- Local OAuth mode: the dashboard and scripts call the Gmail API directly with your own Google OAuth credentials. Use this when you want `Approve & Send` to send automatically from the dashboard after the undo countdown.

The dashboard defaults to Local OAuth mode. Turn on the `Gmail connector` switch when you want approvals to be queued for connector-backed processing instead.

## Local OAuth Environment

Create `.env.local` in this folder. Do not commit it.

```bash
GOOGLE_CLIENT_ID="your-google-oauth-client-id"
GOOGLE_CLIENT_SECRET="your-google-oauth-client-secret"
GOOGLE_REFRESH_TOKEN="your-google-refresh-token"

# Strongly recommended. This is the Gmail account that owns the mailbox.
CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL="you@example.com"

# Required only for OAuth-based inbox import/sync. INBOX works for normal inbox scans.
CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL="INBOX"

# Optional. Defaults to ~/.codex/state/customer-email-assist/customer-email-assist.sqlite3
CUSTOMER_EMAIL_ASSIST_DB_PATH="/tmp/customer-email-assist.sqlite3"

# Optional. Defaults to ./support-policy.md
CUSTOMER_EMAIL_ASSIST_POLICY_PATH="./support-policy.md"
```

## Variable Reference

| Variable | Required? | What it does |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | Required for local OAuth send/sync | Identifies your Google OAuth client. |
| `GOOGLE_CLIENT_SECRET` | Required for local OAuth send/sync | Secret for the OAuth client. Keep it private. |
| `GOOGLE_REFRESH_TOKEN` | Required for local OAuth send/sync | Long-lived token used to get short-lived Gmail access tokens without logging in again. |
| `CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL` | Optional in code, strongly recommended | Your Gmail address. Used to detect outbound human replies and avoid duplicate sends. If omitted, sending can still work, but manual-reply detection is unreliable. |
| `CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL` | Required only for `prepare-inbound-batch` or `sync:oauth` | Gmail label ID to fetch from. Use `INBOX` for inbox import, or a custom Gmail label ID. |
| `CUSTOMER_EMAIL_ASSIST_DB_PATH` | Optional | SQLite database path. |
| `CUSTOMER_EMAIL_ASSIST_POLICY_PATH` | Optional | Local support policy file used when preparing draft evidence. |

## Gmail API Scopes

Use the narrowest scopes that match your flow:

```text
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.readonly
```

`gmail.send` is enough for dashboard auto-send. `gmail.readonly` is needed if the local OAuth scripts also fetch inbound email bodies. Google classifies Gmail scopes by sensitivity, so a public multi-user app may need Google verification. For local single-user testing, keep the OAuth app in Testing mode and add your own Gmail account as a test user.

References:

- Gmail scopes: https://developers.google.com/workspace/gmail/api/auth/scopes
- Gmail send API: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
- Installed app OAuth: https://developers.google.com/identity/protocols/oauth2/native-app
- OAuth testing users: https://support.google.com/cloud/answer/15549945

## Get Google Client ID And Secret

1. Open Google Cloud Console.
2. Create or select a project.
3. Go to APIs & Services, then Library, and enable Gmail API.
4. Go to APIs & Services, then OAuth consent screen.
5. Choose External for a personal Gmail account, or Internal for a Workspace-only app.
6. Keep publishing status as Testing while developing.
7. Add your Gmail account under test users.
8. Go to APIs & Services, then Credentials.
9. Create OAuth client ID.
10. For the easiest refresh-token flow with OAuth Playground, choose Web application and add this authorized redirect URI:

```text
https://developers.google.com/oauthplayground
```

11. Copy the generated client ID and client secret into `.env.local`.

## Get A Refresh Token

Use OAuth 2.0 Playground with your own OAuth client:

1. Open https://developers.google.com/oauthplayground.
2. Click the gear icon.
3. Enable `Use your own OAuth credentials`.
4. Paste your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
5. In the scopes box, enter:

```text
https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly
```

6. Click Authorize APIs.
7. Sign in as the same Gmail account you added as a test user.
8. Approve the consent screen.
9. Click Exchange authorization code for tokens.
10. Copy the refresh token into `.env.local` as `GOOGLE_REFRESH_TOKEN`.

If Google does not return a refresh token, remove the app access from your Google Account permissions and repeat the consent flow. Google often returns a refresh token only on the first explicit offline consent for a client/user/scope combination.

## Run Local OAuth Mode

Install dependencies and initialize the local database:

```bash
npm install
npm run setup-local
```

Start the dashboard:

```bash
npm run dev
```

Fetch/import from Gmail using the local OAuth adapter:

```bash
tsx scripts/customer-email-assist.ts prepare-inbound-batch --out /tmp/prepared-inbound.json
tsx scripts/customer-email-assist.ts import-prepared-batch --input /tmp/prepared-inbound.json
```

Send approved replies from the queue:

```bash
tsx scripts/customer-email-assist.ts apply-send-queue
```

When `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` are present, the dashboard's `Approve & Send` action also attempts the deterministic send path after the undo countdown.

## Security Notes

- Never commit `.env.local`.
- Treat `GOOGLE_REFRESH_TOKEN` like a password.
- Use a dedicated Google Cloud project for this starter.
- Use the smallest Gmail scopes you can.
- If you publish this for many users, expect Google OAuth verification requirements.
