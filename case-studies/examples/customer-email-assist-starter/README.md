# Customer Email Assist Starter

This starter can run in two Gmail modes:

- Connector mode: Codex reads/sends through the Codex Gmail connector. This is easiest inside Codex, but the Next.js dashboard cannot call the connector directly.
- Local OAuth mode: the dashboard and scripts call the Gmail API directly with your own Google OAuth credentials. Use this when you want `Approve & Send` to send automatically from the dashboard after the undo countdown.

The dashboard defaults to Local OAuth mode. Use the `Gmail mode` selector to switch between direct OAuth sends and Gmail connector queue mode.

## Local OAuth Environment

Create `.env.local` in this folder. Do not commit it.

```bash
GOOGLE_CLIENT_ID="your-google-oauth-client-id"
GOOGLE_CLIENT_SECRET="your-google-oauth-client-secret"

# Required only for OAuth-based inbox import/sync. INBOX works for normal inbox scans.
CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL="INBOX"

# Optional. If omitted, the dashboard callback uses the current localhost origin.
GOOGLE_REDIRECT_URI="http://localhost:3002/api/gmail/oauth/callback"

# Optional. The dashboard Connect Gmail flow stores this locally for you.
GOOGLE_REFRESH_TOKEN="your-google-refresh-token"

# Optional. The Connect Gmail flow also detects this from Gmail profile.
CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL="you@example.com"

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
| `GOOGLE_REDIRECT_URI` | Optional | Exact OAuth callback URI. If omitted, the dashboard uses its current origin plus `/api/gmail/oauth/callback`. |
| `GOOGLE_REFRESH_TOKEN` | Optional fallback | Long-lived token used to get short-lived Gmail access tokens. The dashboard Connect Gmail flow writes this to local state automatically, so manual env setup is not required. |
| `CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL` | Optional | Your Gmail address. The Connect Gmail flow detects this from Gmail profile; set it manually only when needed. |
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
- Web server OAuth: https://developers.google.com/identity/protocols/oauth2/web-server
- OAuth testing users: https://support.google.com/cloud/answer/15549945

## Get Google Client ID And Secret

1. Open Google Cloud Console.
2. Create or select a project.
3. Go to APIs & Services, then Library, and enable Gmail API.
4. Go to Google Auth Platform, then Branding, Audience, and Data Access. In older Console layouts this appears as APIs & Services, then OAuth consent screen.
5. Choose External for a personal Gmail account, or Internal for a Workspace-only app.
6. Keep publishing status as Testing while developing.
7. Add your Gmail account under test users.
8. Go to APIs & Services, then Credentials.
9. Create OAuth client ID.
10. Choose Web application and add the dashboard callback URI as an authorized redirect URI. Use the exact host and port where the dashboard runs:

```text
http://localhost:3002/api/gmail/oauth/callback
```

If you run `npm run dev` on the default Next.js port, use:

```text
http://localhost:3000/api/gmail/oauth/callback
```

11. Copy the generated client ID and client secret into `.env.local`.

## Connect Gmail From The Dashboard

After `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set:

1. Restart the dashboard.
2. Leave `Gmail mode` set to `OAuth`.
3. Click `Connect Gmail`.
4. Approve the Gmail consent screen.
5. The callback stores the refresh token in local state at `~/.codex/state/customer-email-assist/gmail-oauth.json`.

OAuth Playground is no longer the primary path. Keep it only as a manual fallback if you are testing the raw OAuth flow outside the dashboard.

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

When the dashboard has a connected local OAuth token, `Approve & Send` attempts the deterministic send path after the undo countdown.

## Security Notes

- Never commit `.env.local`.
- Treat the stored Gmail OAuth file like a password.
- Use a dedicated Google Cloud project for this starter.
- Use the smallest Gmail scopes you can.
- If you publish this for many users, expect Google OAuth verification requirements.
