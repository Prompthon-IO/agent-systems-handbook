# Discord Lab Updates Automation

This repository enqueues Discord announcement jobs for Agentic Labs GitHub
events: issue `good-first-issue` labels, PR coordination, PR merges, and direct
pushes to `main`.
A separate local announcer worker drains those jobs from Postgres and posts
them to the Agentic Labs Discord channels.

## Required GitHub Secret

Create this repository secret in GitHub Actions:

```txt
PATHWAY_DISCORD_ANNOUNCER_DATABASE_URL
```

Use the same remote Postgres URL configured for the local announcer worker's
`PATHWAY_DISCORD_ANNOUNCER_DATABASE_URL` value.

Do not commit the value.

## Required GitHub Variables

After CaraP creates the Agentic Labs channels, sync routes from the
`agent_skills` repo and copy the printed values into GitHub repository
variables:

```txt
DISCORD_REPO_UPDATES_CHANNEL_ID
DISCORD_GOOD_FIRST_ISSUES_CHANNEL_ID
DISCORD_CODE_REVIEW_CHANNEL_ID
```

## Local Workflow Test

From this repository root:

```bash
node .github/scripts/enqueue-discord-announcement.mjs --dry-run
```

The dry run prints only job metadata and channel targets. It does not connect to
Postgres and does not post to Discord.

## Runtime Flow

1. A matching issue, PR, or direct `main` push event lands in GitHub.
2. `.github/workflows/discord-lab-updates.yml` checks out the repo and runs the
   enqueue script.
3. The script inserts one or more deduped rows into
   `discord_announcement_jobs`.
4. Nova P posts regular feed and PR coordination messages.
5. CaraP handles channel setup and settings changes.

For forked PRs, GitHub does not expose repository secrets to the
`pull_request` run. Those untrusted PR runs skip the database write, and the
trusted `main` push that follows a merge enqueues the same PR-merge announcement
using the PR dedupe key.
