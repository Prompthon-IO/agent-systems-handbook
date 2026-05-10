#!/usr/bin/env node

import fs from "node:fs";

import {
  extractLabelNames,
  extractTrackFromLabels,
  findLinkedIssueNumbers,
  validateChangedFilesForTrack,
} from "./prompthon-activity-policy.mjs";

const COMMENT_MARKER = "<!-- prompthon-track-guard -->";

function readEventPayload() {
  const eventPath = process.env.GITHUB_EVENT_PATH;
  if (!eventPath || !fs.existsSync(eventPath)) {
    return {};
  }
  return JSON.parse(fs.readFileSync(eventPath, "utf8"));
}

async function githubRequest(path, options = {}) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error("GITHUB_TOKEN is required.");
  }
  const response = await fetch(`https://api.github.com${path}`, {
    ...options,
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
      "user-agent": "prompthon-track-guard",
      "x-github-api-version": "2022-11-28",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    throw new Error(`GitHub API ${response.status}: ${await response.text()}`);
  }
  return response.status === 204 ? null : response.json();
}

async function listPullRequestFiles(repo, pullNumber) {
  const files = [];
  for (let page = 1; page <= 20; page += 1) {
    const batch = await githubRequest(
      `/repos/${repo}/pulls/${pullNumber}/files?per_page=100&page=${page}`,
    );
    files.push(...batch.map((file) => file.filename).filter(Boolean));
    if (batch.length < 100) {
      break;
    }
  }
  return files;
}

async function upsertFailureComment(repo, pullNumber, body) {
  const comments = await githubRequest(`/repos/${repo}/issues/${pullNumber}/comments?per_page=100`);
  const existing = comments.find((comment) =>
    typeof comment.body === "string" && comment.body.includes(COMMENT_MARKER),
  );
  if (existing) {
    await githubRequest(`/repos/${repo}/issues/comments/${existing.id}`, {
      method: "PATCH",
      body: JSON.stringify({ body }),
    });
    return;
  }
  await githubRequest(`/repos/${repo}/issues/${pullNumber}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

function failureComment({ allowedPaths, invalidFiles, track }) {
  return [
    COMMENT_MARKER,
    `prompthon-track-guard found files outside the allowed ${track} paths.`,
    "",
    "Allowed paths:",
    ...allowedPaths.map((path) => `- \`${path}\``),
    "",
    "Invalid files:",
    ...invalidFiles.map((path) => `- \`${path}\``),
  ].join("\n");
}

async function main() {
  const dryRun = process.argv.includes("--dry-run");
  const event = readEventPayload();
  const pullRequest = event.pull_request;
  const repo = event.repository?.full_name || process.env.GITHUB_REPOSITORY;
  if (!pullRequest?.number || !repo) {
    console.log(JSON.stringify({ skipped: true, reason: "missing_pull_request_payload" }, null, 2));
    return;
  }

  const linkedIssueNumbers = findLinkedIssueNumbers(pullRequest.body);
  const linkedIssueNumber = linkedIssueNumbers[0] || null;
  const linkedIssue = linkedIssueNumber
    ? await githubRequest(`/repos/${repo}/issues/${linkedIssueNumber}`)
    : null;
  const issueLabels = extractLabelNames(linkedIssue?.labels);
  const prLabels = extractLabelNames(pullRequest.labels);
  const track = extractTrackFromLabels(issueLabels) || extractTrackFromLabels(prLabels);
  const changedFiles = dryRun && Array.isArray(event.changed_files)
    ? event.changed_files
    : await listPullRequestFiles(repo, pullRequest.number);

  if (!track) {
    const message = "prompthon-track-guard could not determine a contribution track from the linked issue or PR labels.";
    if (!dryRun) {
      await upsertFailureComment(repo, pullRequest.number, `${COMMENT_MARKER}\n${message}`);
    }
    console.error(message);
    process.exitCode = 1;
    return;
  }

  const validation = validateChangedFilesForTrack(track, changedFiles);
  const summary = {
    changedFiles,
    linkedIssueNumber,
    track,
    ...validation,
  };

  if (!validation.valid) {
    if (!dryRun) {
      await upsertFailureComment(repo, pullRequest.number, failureComment({ track, ...validation }));
    }
    console.error(JSON.stringify(summary, null, 2));
    process.exitCode = 1;
    return;
  }

  console.log(JSON.stringify({ status: "passed", ...summary }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
