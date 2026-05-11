# Discord Lab Updates Automation

This repository enqueues Discord announcement jobs for Agentic Labs GitHub
events: issue `good-first-issue` labels, PR coordination for `develop` and
`main`, PR merges, direct pushes to `main`, and production handbook releases.
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

After Keira creates or verifies the Agentic Labs channels, sync routes from the
`agent_skills` repo and copy the printed values into GitHub repository
variables:

```txt
DISCORD_REPO_UPDATES_CHANNEL_ID
DISCORD_GOOD_FIRST_ISSUES_CHANNEL_ID
DISCORD_CODE_REVIEW_CHANNEL_ID
DISCORD_PROJECT_ANNOUNCEMENTS_CHANNEL_ID
```

`HANDBOOK_DEPLOYED_URL` is optional. If unset, release announcements use
`https://labs.prompthon.io`. `DISCORD_PROJECT_ANNOUNCEMENTS_CHANNEL_ID` should
be set in repository variables, but the release workflow keeps the current live
project-announcements channel id as a fallback.

## Local Workflow Test

From this repository root:

```bash
node .github/scripts/enqueue-discord-announcement.mjs --dry-run
```

The dry run prints only job metadata and channel targets. It does not connect to
Postgres and does not post to Discord.

## Runtime Flow

1. A matching issue, `develop` or `main` PR, direct `main` push, or release
   event lands in GitHub.
2. `.github/workflows/discord-lab-updates.yml` checks out the repo and runs the
   enqueue script.
3. The script inserts one or more deduped rows into
   `discord_announcement_jobs`.
4. `.github/workflows/release-main.yml` creates the GitHub release for a
   successful `develop` to `main` release, then enqueues a
   `handbook_release_published` job for `#project-announcements`.
5. Keira posts release announcements with the release link, deployed handbook
   URL, major changes, and the explicit `@everyone` mention.

For forked PRs, GitHub does not expose repository secrets to the
`pull_request` run. Those untrusted PR runs skip the database write, and the
trusted `main` push that follows a merge enqueues the same PR-merge announcement
using the PR dedupe key.
