#!/usr/bin/env node

import fs from "node:fs";

import {
  extractLabelNames,
  findLinkedIssueNumbers,
  validateChangedFilesForTrack,
} from "./prompthon-activity-policy.mjs";

import { resolveClassification } from "./prompthon-pr-classification.mjs";

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

async function tryUpsertFailureComment(repo, pullNumber, body) {
  try {
    await upsertFailureComment(repo, pullNumber, body);
  } catch (error) {
    console.warn(
      `Warning: could not write prompthon-track-guard failure comment: ${error.message}`,
    );
  }
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

function reportFailure(message) {
  // Keep the actionable failure visible even when GitHub rejects the comment.
  console.error(message);
  if (process.env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${message}\n`);
  }
  process.exitCode = 1;
}

function isReleasePullRequest(pullRequest, repo) {
  return pullRequest.base?.ref === "main" &&
    pullRequest.head?.ref === "develop" &&
    pullRequest.head?.repo?.full_name === repo;
}

async function main() {
  const dryRun = process.argv.includes("--dry-run");
  const event = readEventPayload();
  let pullRequest = event.pull_request;
  const repo = event.repository?.full_name || process.env.GITHUB_REPOSITORY;
  if (!pullRequest?.number || !repo) {
    console.log(JSON.stringify({ skipped: true, reason: "missing_pull_request_payload" }, null, 2));
    return;
  }

  // Serialize runs and read current metadata: event snapshots can predate label edits.
  if (!dryRun) pullRequest = await githubRequest(`/repos/${repo}/pulls/${pullRequest.number}`);
  if (pullRequest.state === "closed") return;
  if (isReleasePullRequest(pullRequest, repo)) {
    console.log(JSON.stringify({
      skipped: true,
      reason: "develop_to_main_release_pr",
    }, null, 2));
    return;
  }

  const linkedIssueNumbers = findLinkedIssueNumbers(pullRequest.body);
  const linkedIssues = [];
  for (const number of linkedIssueNumbers) {
    const issue = await githubRequest(`/repos/${repo}/issues/${number}`);
    if (issue.pull_request) throw new Error(`#${number} is a PR; link an Issue for classification inheritance.`);
    linkedIssues.push({ ...issue, number });
  }
  let classification;
  try {
    classification = resolveClassification({ body: pullRequest.body, labels: pullRequest.labels, issues: linkedIssues });
  } catch (error) {
    const message = `prompthon-track-guard: ${error.message}\n\nExample for a skill package:\n## Repository track\n- [x] \`practitioner\`\n## Work kind\n- [x] \`skill-package\`\n\nChoose the values matching your contribution; paths are still validated.`;
    reportFailure(message);
    if (!dryRun) await tryUpsertFailureComment(repo, pullRequest.number, `${COMMENT_MARKER}\n${message}`);
    return;
  }
  const { track } = classification;
  const changedFiles = dryRun && Array.isArray(event.changed_files)
    ? event.changed_files
    : await listPullRequestFiles(repo, pullRequest.number);
  const validation = validateChangedFilesForTrack(track, changedFiles);
  const summary = {
    changedFiles,
    linkedIssueNumbers,
    kind: classification.kind,
    track,
    ...validation,
  };

  if (!validation.valid) {
    reportFailure(failureComment({ track, ...validation }));
    if (!dryRun) {
      await tryUpsertFailureComment(repo, pullRequest.number, failureComment({ track, ...validation }));
    }
    console.error(JSON.stringify(summary, null, 2));
    return;
  }

  if (!dryRun) {
    const latest = await githubRequest(`/repos/${repo}/pulls/${pullRequest.number}`);
    if (latest.state === "closed" || latest.head?.sha !== pullRequest.head?.sha || latest.body !== pullRequest.body ||
        JSON.stringify(extractLabelNames(latest.labels).sort()) !== JSON.stringify(extractLabelNames(pullRequest.labels).sort())) {
      throw new Error("PR changed during classification; rerun against the current metadata and commit.");
    }
    const missing = classification.labels.filter(label => !extractLabelNames(pullRequest.labels).includes(label));
    if (missing.length) {
      await githubRequest(`/repos/${repo}/issues/${pullRequest.number}/labels`, {
        method: "POST", body: JSON.stringify({ labels: missing }),
      });
    }
    const persisted = await githubRequest(`/repos/${repo}/issues/${pullRequest.number}/labels`);
    // Recheck the authoritative labels, including conflicting labels added concurrently.
    resolveClassification({ body: pullRequest.body, labels: persisted, issues: linkedIssues });
    if (classification.labels.some(label => !extractLabelNames(persisted).includes(label))) {
      throw new Error("Classification labels were not persisted; rerun the check.");
    }
    // Adding labels with GITHUB_TOKEN does not trigger a second workflow. This run
    // completes validation and replaces the old failure message itself.
    await tryUpsertFailureComment(repo, pullRequest.number,
      `${COMMENT_MARKER}\nClassification and path checks passed: \`${classification.labels.join("\`, \`")}\`. No model inference was used. This does not approve or merge the PR.`);
  }
  console.log(JSON.stringify({ status: "passed", ...summary }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
