#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const GOOD_FIRST_LABEL = "good-first-issue";
const ELIGIBLE_PREFIXES = [
  "case-studies/",
  "contributor-kit/",
  "ecosystem/",
  "foundations/",
  "patterns/",
  "publications/",
  "radar/",
  "reading-paths/",
  "skills/",
  "systems/",
  "zh-Hans/",
];
const ELIGIBLE_FILES = new Set([
  "CODE_OF_CONDUCT.md",
  "CONTRIBUTING.md",
  "README.md",
  "SECURITY.md",
  "SUPPORT.md",
]);

function parseArgs(argv) {
  return {
    dryRun: argv.includes("--dry-run"),
  };
}

function runGit(args, fallback = "") {
  try {
    return execFileSync("git", args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return fallback;
  }
}

function readEventPayload() {
  const eventPath = process.env.GITHUB_EVENT_PATH;
  if (!eventPath || !fs.existsSync(eventPath)) {
    return {};
  }
  return JSON.parse(fs.readFileSync(eventPath, "utf8"));
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function isZeroSha(value) {
  return typeof value === "string" && /^0+$/.test(value);
}

function changedPathsFromGit({ before, sha }) {
  const diffArgs =
    before && sha && !isZeroSha(before)
      ? ["diff", "--name-only", before, sha]
      : ["diff-tree", "--no-commit-id", "--name-only", "-r", sha || "HEAD"];
  const output = runGit(diffArgs);
  return output ? output.split(/\r?\n/).filter(Boolean) : [];
}

function isEligiblePath(filePath) {
  return ELIGIBLE_FILES.has(filePath) ||
    ELIGIBLE_PREFIXES.some((prefix) => filePath.startsWith(prefix));
}

function firstLine(value) {
  return String(value || "").split(/\r?\n/)[0]?.trim() || "";
}

function firstParagraph(value) {
  return String(value || "")
    .split(/\r?\n\r?\n/)
    .map((part) => part.replace(/\s+/g, " ").trim())
    .find(Boolean) || "";
}

function truncate(value, maxLength) {
  const text = String(value || "").trim();
  if (text.length <= maxLength) {
    return text;
  }
  const ellipsis = "...";
  if (maxLength <= ellipsis.length) {
    return ellipsis.slice(0, Math.max(0, maxLength));
  }
  return `${text.slice(0, maxLength - ellipsis.length).trim()}${ellipsis}`;
}

function channelIdFor(key) {
  if (key === "repo-updates") {
    return process.env.DISCORD_REPO_UPDATES_CHANNEL_ID || process.env.DISCORD_LAB_UPDATES_CHANNEL_ID || null;
  }
  if (key === "good-first-issues-feed") {
    return process.env.DISCORD_GOOD_FIRST_ISSUES_CHANNEL_ID || null;
  }
  if (key === "code-review") {
    return process.env.DISCORD_CODE_REVIEW_CHANNEL_ID || process.env.DISCORD_PULL_REQUESTS_CHANNEL_ID || null;
  }
  return null;
}

function normalizeGitHubRepoFullName(value) {
  return String(value || "")
    .trim()
    .replace(/\.git$/, "")
    .replace(/^https?:\/\/github\.com\//, "")
    .replace(/^git@github\.com:/, "")
    .replace(/^ssh:\/\/git@github\.com\//, "")
    .replace(/\/$/, "");
}

function baseRepoInfo(event) {
  const repoFullName = normalizeGitHubRepoFullName(
    process.env.GITHUB_REPOSITORY ||
    event.repository?.full_name ||
    runGit(["config", "--get", "remote.origin.url"], "Prompthon-IO/agent-systems-handbook"),
  );
  return {
    repoFullName,
    repoUrl: event.repository?.html_url || `https://github.com/${repoFullName}`,
  };
}

function summarizeAreas(paths) {
  const areas = unique(
    paths.map((filePath) => {
      if (ELIGIBLE_FILES.has(filePath)) {
        return filePath;
      }
      return filePath.split("/")[0];
    }),
  ).slice(0, 4);

  if (!areas.length) {
    return "lab content";
  }
  if (areas.length === 1) {
    return areas[0];
  }
  return `${areas.slice(0, -1).join(", ")} and ${areas.at(-1)}`;
}

function labels(issue) {
  return (issue?.labels ?? [])
    .map((label) => typeof label === "string" ? label : label?.name)
    .filter(Boolean);
}

function hasGoodFirstLabel(issue) {
  return labels(issue).some((label) => label.toLowerCase() === GOOD_FIRST_LABEL);
}

async function fetchAssociatedPullRequest({ repoFullName, sha, token }) {
  if (!repoFullName || !sha || !token || !globalThis.fetch) {
    return null;
  }

  const response = await fetch(
    `https://api.github.com/repos/${repoFullName}/commits/${sha}/pulls`,
    {
      headers: {
        accept: "application/vnd.github+json",
        authorization: `Bearer ${token}`,
        "user-agent": "pathway-discord-announcer",
        "x-github-api-version": "2022-11-28",
      },
    },
  );

  if (!response.ok) {
    return null;
  }
  const pulls = await response.json();
  return Array.isArray(pulls) && pulls.length ? pulls[0] : null;
}

function makeJob({
  authorLogin = null,
  branch = process.env.GITHUB_REF_NAME || "main",
  changeSummary = null,
  changedPaths = [],
  channelKey,
  commitSha = process.env.GITHUB_SHA || null,
  dedupeKey,
  eventType,
  mergedByLogin = null,
  payloadJson = {},
  prNumber = null,
  prTitle = null,
  prUrl = null,
  repoFullName,
  repoUrl,
}) {
  return {
    authorLogin,
    branch,
    changeSummary,
    changedPaths,
    channelKey,
    commitSha,
    dedupeKey,
    discordChannelId: channelIdFor(channelKey),
    eligiblePathCount: changedPaths.length,
    eventType,
    maxAttempts: Number.parseInt(process.env.ANNOUNCER_MAX_ATTEMPTS || "5", 10),
    mergedByLogin,
    payloadJson: {
      eventName: process.env.GITHUB_EVENT_NAME || null,
      githubRunId: process.env.GITHUB_RUN_ID || null,
      workflow: process.env.GITHUB_WORKFLOW || null,
      ...payloadJson,
    },
    prNumber,
    prTitle,
    prUrl,
    repoFullName,
    repoUrl,
  };
}

async function buildPushJobs(event) {
  const { repoFullName, repoUrl } = baseRepoInfo(event);
  const sha = process.env.GITHUB_SHA || event.after || runGit(["rev-parse", "HEAD"]);
  const branch =
    process.env.GITHUB_REF_NAME ||
    event.ref?.replace("refs/heads/", "") ||
    runGit(["branch", "--show-current"], "main");
  const pullRequest = await fetchAssociatedPullRequest({
    repoFullName,
    sha,
    token: process.env.GITHUB_TOKEN,
  });

  if (pullRequest) {
    return [
      makeJob({
        authorLogin: pullRequest.user?.login || null,
        branch,
        changeSummary: truncate(firstParagraph(pullRequest.body), 700) || `Merged PR #${pullRequest.number}.`,
        channelKey: "repo-updates",
        commitSha: sha,
        dedupeKey: `${repoFullName}:pr:${pullRequest.number}:merged:repo-updates`,
        eventType: "github_pr_merged",
        mergedByLogin: pullRequest.merged_by?.login ||
          event.head_commit?.committer?.username ||
          process.env.GITHUB_ACTOR ||
          null,
        payloadJson: {
          pull_request: pullRequest,
          sourceUrl: pullRequest.html_url,
        },
        prNumber: pullRequest.number,
        prTitle: pullRequest.title,
        prUrl: pullRequest.html_url,
        repoFullName,
        repoUrl,
      }),
    ];
  }

  const before = event.before || runGit(["rev-parse", `${sha}^`], "");
  const changedPaths = changedPathsFromGit({ before, sha });
  const eligiblePaths = unique(changedPaths.filter(isEligiblePath));
  if (!eligiblePaths.length) {
    return [];
  }

  const headCommit = event.head_commit || {};
  const commitMessage = headCommit.message || runGit(["log", "-1", "--pretty=%B"]);
  const commitTitle = firstLine(commitMessage) || "Repository update";
  const changeSummary = truncate(
    [
      `Updated ${summarizeAreas(eligiblePaths)}.`,
      firstParagraph(commitMessage) || `Latest direct main update: ${commitTitle}`,
    ].join(" "),
    700,
  );
  const commitUrl = headCommit.url || `${repoUrl}/commit/${sha}`;

  return [
    makeJob({
      authorLogin: headCommit.author?.username || process.env.GITHUB_ACTOR || null,
      branch,
      changeSummary,
      changedPaths: eligiblePaths,
      channelKey: "repo-updates",
      commitSha: sha,
      dedupeKey: `${repoFullName}:${branch}:${sha}:repo-updates`,
      eventType: "github_push_main",
      mergedByLogin: headCommit.committer?.username || process.env.GITHUB_ACTOR || null,
      payloadJson: {
        allChangedPaths: changedPaths,
        headCommitUrl: commitUrl,
        sourceUrl: commitUrl,
      },
      prTitle: commitTitle,
      repoFullName,
      repoUrl,
    }),
  ];
}

function buildIssueJobs(event) {
  const action = event.action;
  const issue = event.issue;
  if (!issue || !hasGoodFirstLabel(issue)) {
    return [];
  }

  const { repoFullName, repoUrl } = baseRepoInfo(event);
  const issueNumber = issue.number;
  const issueSummary = truncate(firstParagraph(issue.body), 700);
  const commonPayload = {
    issue,
    issueSummary,
    issueUrl: issue.html_url,
  };

  if (["opened", "labeled", "edited", "reopened"].includes(action)) {
    return [
      makeJob({
        authorLogin: event.sender?.login || issue.user?.login || null,
        changeSummary: issueSummary || "A new contributor-friendly issue is ready.",
        channelKey: "good-first-issues-feed",
        dedupeKey: `${repoFullName}:issue:${issueNumber}:good-first-feed`,
        eventType: "github_issue_good_first_feed",
        payloadJson: commonPayload,
        prNumber: issueNumber,
        prTitle: issue.title,
        prUrl: issue.html_url,
        repoFullName,
        repoUrl,
      }),
    ];
  }

  if (action === "closed") {
    return [];
  }

  return [];
}

function buildPullRequestJobs(event) {
  const action = event.action;
  const pullRequest = event.pull_request;
  if (!pullRequest) {
    return [];
  }
  if (pullRequest.base?.ref !== "main") {
    return [];
  }

  const { repoFullName, repoUrl } = baseRepoInfo(event);
  if (["opened", "reopened", "ready_for_review"].includes(action)) {
    return [
      makeJob({
        authorLogin: event.sender?.login || pullRequest.user?.login || null,
        changeSummary: truncate(firstParagraph(pullRequest.body), 700),
        channelKey: "code-review",
        commitSha: pullRequest.head?.sha || process.env.GITHUB_SHA || null,
        dedupeKey: `${repoFullName}:pr:${pullRequest.number}:${action}:code-review`,
        eventType: `github_pull_request_${action}`,
        payloadJson: {
          pull_request: pullRequest,
          sourceUrl: pullRequest.html_url,
        },
        prNumber: pullRequest.number,
        prTitle: pullRequest.title,
        prUrl: pullRequest.html_url,
        repoFullName,
        repoUrl,
      }),
    ];
  }

  if (baseRef !== "main") {
    return [];
  }

  if (action === "closed" && pullRequest.merged) {
    const changedPaths = [];
    return [
      makeJob({
        authorLogin: pullRequest.user?.login || null,
        changeSummary: truncate(firstParagraph(pullRequest.body), 700) || `Merged PR #${pullRequest.number}.`,
        changedPaths,
        channelKey: "repo-updates",
        commitSha: pullRequest.merge_commit_sha || process.env.GITHUB_SHA || null,
        dedupeKey: `${repoFullName}:pr:${pullRequest.number}:merged:repo-updates`,
        eventType: "github_pr_merged",
        mergedByLogin: pullRequest.merged_by?.login || event.sender?.login || null,
        payloadJson: {
          pull_request: pullRequest,
          sourceUrl: pullRequest.html_url,
        },
        prNumber: pullRequest.number,
        prTitle: pullRequest.title,
        prUrl: pullRequest.html_url,
        repoFullName,
        repoUrl,
      }),
    ];
  }

  return [];
}

async function buildJobs(event) {
  const eventName = process.env.GITHUB_EVENT_NAME || event.event_name || "";
  if (eventName === "issues") {
    return buildIssueJobs(event);
  }
  if (eventName === "pull_request") {
    return buildPullRequestJobs(event);
  }
  return buildPushJobs(event);
}

function publicJobSummary(job) {
  return {
    channelKey: job.channelKey,
    commitSha: job.commitSha,
    dedupeKey: job.dedupeKey,
    discordChannelId: job.discordChannelId,
    eventType: job.eventType,
    prNumber: job.prNumber,
    prTitle: job.prTitle,
    repoFullName: job.repoFullName,
    sourceUrl: job.payloadJson?.sourceUrl || job.payloadJson?.issueUrl || null,
  };
}

function isForkPullRequestJob(job) {
  if (job.payloadJson?.eventName !== "pull_request") {
    return false;
  }

  const headRepoFullName = normalizeGitHubRepoFullName(
    job.payloadJson?.pull_request?.head?.repo?.full_name,
  );
  return Boolean(headRepoFullName && headRepoFullName !== job.repoFullName);
}

function wantsSsl(databaseUrl) {
  return /(?:[?&]ssl=true|[?&]sslmode=(?:require|prefer|verify-ca|verify-full))/i.test(
    databaseUrl,
  );
}

async function enqueueJob(job) {
  const databaseUrl = process.env.PATHWAY_DISCORD_ANNOUNCER_DATABASE_URL;
  if (!databaseUrl) {
    if (process.env.GITHUB_ACTIONS === "true" && isForkPullRequestJob(job)) {
      return { skipped: true, reason: "fork_pull_request_secrets_unavailable" };
    }

    const message = "Missing required PATHWAY_DISCORD_ANNOUNCER_DATABASE_URL secret; cannot enqueue Discord announcement job.";
    if (process.env.GITHUB_ACTIONS === "true") {
      console.error(`::error::${message}`);
      throw new Error(message);
    }
    return { skipped: true, reason: "missing_database_secret" };
  }
  if (!job.discordChannelId && job.eventType !== "github_issue_closed_archive_thread") {
    return { skipped: true, reason: "missing_discord_channel_id" };
  }

  const { Client } = require("pg");
  const allowInsecureSsl = process.env.PATHWAY_DISCORD_ANNOUNCER_ALLOW_INSECURE_SSL === "true";
  const client = new Client({
    connectionString: databaseUrl,
    ssl: wantsSsl(databaseUrl) ? { rejectUnauthorized: !allowInsecureSsl } : undefined,
  });

  await client.connect();
  try {
    const result = await client.query(
      `
        INSERT INTO discord_announcement_jobs (
          dedupe_key,
          event_type,
          repo_full_name,
          repo_url,
          branch,
          commit_sha,
          pr_number,
          pr_title,
          pr_url,
          merged_by_login,
          author_login,
          change_summary,
          changed_paths,
          eligible_path_count,
          channel_key,
          discord_channel_id,
          max_attempts,
          payload_json
        )
        VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8,
          $9, $10, $11, $12, $13, $14, $15, $16,
          $17, $18::jsonb
        )
        ON CONFLICT (dedupe_key) DO NOTHING
        RETURNING id, status
      `,
      [
        job.dedupeKey,
        job.eventType,
        job.repoFullName,
        job.repoUrl,
        job.branch,
        job.commitSha,
        job.prNumber,
        job.prTitle,
        job.prUrl,
        job.mergedByLogin,
        job.authorLogin,
        job.changeSummary,
        job.changedPaths,
        job.eligiblePathCount,
        job.channelKey,
        job.discordChannelId,
        job.maxAttempts,
        JSON.stringify(job.payloadJson),
      ],
    );

    if (result.rowCount > 0) {
      return {
        created: true,
        id: result.rows[0].id,
        status: result.rows[0].status,
      };
    }

    const existing = await client.query(
      "SELECT id, status FROM discord_announcement_jobs WHERE dedupe_key = $1",
      [job.dedupeKey],
    );
    return {
      created: false,
      id: existing.rows[0]?.id ?? null,
      status: existing.rows[0]?.status ?? null,
    };
  } finally {
    await client.end();
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const event = readEventPayload();
  const jobs = await buildJobs(event);

  if (!jobs.length) {
    console.log(JSON.stringify({ skipped: true, reason: "no_matching_event" }, null, 2));
    return;
  }

  if (options.dryRun) {
    console.log(
      JSON.stringify(
        {
          dryRun: true,
          jobs: jobs.map(publicJobSummary),
        },
        null,
        2,
      ),
    );
    return;
  }

  const results = [];
  for (const job of jobs) {
    const result = await enqueueJob(job);
    results.push({
      ...result,
      summary: publicJobSummary(job),
    });
  }
  console.log(JSON.stringify({ results }, null, 2));
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
