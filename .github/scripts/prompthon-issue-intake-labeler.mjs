#!/usr/bin/env node

import fs from "node:fs";

import { labelsForIssueBody } from "./prompthon-activity-policy.mjs";

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
      "user-agent": "prompthon-issue-intake-labeler",
      "x-github-api-version": "2022-11-28",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    throw new Error(`GitHub API ${response.status}: ${await response.text()}`);
  }
  return response.status === 204 ? null : response.json();
}

async function main() {
  const dryRun = process.argv.includes("--dry-run");
  const event = readEventPayload();
  const issue = event.issue;
  const repo = event.repository?.full_name || process.env.GITHUB_REPOSITORY;
  if (!issue?.number || !repo) {
    console.log(JSON.stringify({ skipped: true, reason: "missing_issue_payload" }, null, 2));
    return;
  }

  const labels = labelsForIssueBody(issue.body);
  if (!labels.length) {
    console.log(JSON.stringify({ skipped: true, reason: "no_activity_labels" }, null, 2));
    return;
  }

  if (dryRun) {
    console.log(JSON.stringify({ dryRun: true, issue: issue.number, labels }, null, 2));
    return;
  }

  await githubRequest(`/repos/${repo}/issues/${issue.number}/labels`, {
    method: "POST",
    body: JSON.stringify({ labels }),
  });
  console.log(JSON.stringify({ issue: issue.number, labels, status: "labeled" }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
