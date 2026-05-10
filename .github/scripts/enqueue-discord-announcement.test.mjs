import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const scriptPath = path.join(__dirname, "enqueue-discord-announcement.mjs");
const repoRoot = path.resolve(__dirname, "../..");

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

test("trusted main push for an associated fork PR enqueues the PR merge announcement", () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "discord-announcer-"));
  const eventPath = path.join(tempDir, "event.json");
  const fetchPreloadPath = path.join(tempDir, "mock-fetch.mjs");
  const mergeSha = "9a91452002bd2f7db8e9b329cbddc4d6985f05dd";

  writeJson(eventPath, {
    after: mergeSha,
    before: "3d7168117324528ca26fc25bb7ff51ab42b2a34e",
    ref: "refs/heads/main",
    repository: {
      full_name: "Prompthon-IO/agent-systems-handbook",
      html_url: "https://github.com/Prompthon-IO/agent-systems-handbook",
    },
  });

  fs.writeFileSync(
    fetchPreloadPath,
    `
globalThis.fetch = async () => new Response(JSON.stringify([
  {
    number: 71,
    title: "feat: add personal-knowledge-capture skill package",
    html_url: "https://github.com/Prompthon-IO/agent-systems-handbook/pull/71",
    user: { login: "emptyshell424" }
  }
]));
`,
  );

  const result = spawnSync(
    process.execPath,
    ["--import", fetchPreloadPath, scriptPath, "--dry-run"],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        DISCORD_REPO_UPDATES_CHANNEL_ID: "1499430188105334996",
        GITHUB_EVENT_NAME: "push",
        GITHUB_EVENT_PATH: eventPath,
        GITHUB_REF_NAME: "main",
        GITHUB_REPOSITORY: "Prompthon-IO/agent-systems-handbook",
        GITHUB_SHA: mergeSha,
        GITHUB_TOKEN: "test-token",
      },
    },
  );

  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.equal(output.dryRun, true);
  assert.deepEqual(output.jobs, [
    {
      channelKey: "repo-updates",
      commitSha: mergeSha,
      dedupeKey: "Prompthon-IO/agent-systems-handbook:pr:71:merged:repo-updates",
      discordChannelId: "1499430188105334996",
      eventType: "github_pr_merged",
      prNumber: 71,
      prTitle: "feat: add personal-knowledge-capture skill package",
      repoFullName: "Prompthon-IO/agent-systems-handbook",
      sourceUrl: "https://github.com/Prompthon-IO/agent-systems-handbook/pull/71",
    },
  ]);
});

test("fork pull request events skip cleanly when Actions secrets are unavailable", () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "discord-announcer-"));
  const eventPath = path.join(tempDir, "event.json");
  const mergeSha = "9a91452002bd2f7db8e9b329cbddc4d6985f05dd";

  writeJson(eventPath, {
    action: "closed",
    repository: {
      full_name: "Prompthon-IO/agent-systems-handbook",
      html_url: "https://github.com/Prompthon-IO/agent-systems-handbook",
    },
    pull_request: {
      base: {
        ref: "main",
      },
      body: "",
      head: {
        repo: {
          full_name: "emptyshell424/agent-systems-handbook",
        },
        sha: "46398001c783afc154329826b51c86b06b4a9b9e",
      },
      html_url: "https://github.com/Prompthon-IO/agent-systems-handbook/pull/71",
      merge_commit_sha: mergeSha,
      merged: true,
      merged_by: {
        login: "dprat0821",
      },
      number: 71,
      title: "feat: add personal-knowledge-capture skill package",
      user: {
        login: "emptyshell424",
      },
    },
    sender: {
      login: "dprat0821",
    },
  });

  const env = {
    ...process.env,
    ANNOUNCER_MAX_ATTEMPTS: "5",
    DISCORD_REPO_UPDATES_CHANNEL_ID: "1499430188105334996",
    GITHUB_ACTIONS: "true",
    GITHUB_EVENT_NAME: "pull_request",
    GITHUB_EVENT_PATH: eventPath,
    GITHUB_REF_NAME: "feat/personal-knowledge-capture",
    GITHUB_REPOSITORY: "Prompthon-IO/agent-systems-handbook",
    GITHUB_SHA: "46398001c783afc154329826b51c86b06b4a9b9e",
  };
  delete env.PATHWAY_DISCORD_ANNOUNCER_DATABASE_URL;

  const result = spawnSync(process.execPath, [scriptPath], {
    cwd: repoRoot,
    encoding: "utf8",
    env,
  });

  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.deepEqual(output.results, [
    {
      reason: "fork_pull_request_secrets_unavailable",
      skipped: true,
      summary: {
        channelKey: "repo-updates",
        commitSha: mergeSha,
        dedupeKey: "Prompthon-IO/agent-systems-handbook:pr:71:merged:repo-updates",
        discordChannelId: "1499430188105334996",
        eventType: "github_pr_merged",
        prNumber: 71,
        prTitle: "feat: add personal-knowledge-capture skill package",
        repoFullName: "Prompthon-IO/agent-systems-handbook",
        sourceUrl: "https://github.com/Prompthon-IO/agent-systems-handbook/pull/71",
      },
    },
  ]);
});

test("develop pull request events enqueue code review coordination", () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "discord-announcer-"));
  const eventPath = path.join(tempDir, "event.json");

  writeJson(eventPath, {
    action: "opened",
    repository: {
      full_name: "Prompthon-IO/agent-systems-handbook",
      html_url: "https://github.com/Prompthon-IO/agent-systems-handbook",
    },
    pull_request: {
      base: {
        ref: "develop",
      },
      body: "Adds a focused contributor guide.",
      head: {
        repo: {
          full_name: "Prompthon-IO/agent-systems-handbook",
        },
        sha: "abc123",
      },
      html_url: "https://github.com/Prompthon-IO/agent-systems-handbook/pull/99",
      number: 99,
      title: "docs: add contributor guide",
      user: {
        login: "contributor",
      },
    },
    sender: {
      login: "contributor",
    },
  });

  const result = spawnSync(process.execPath, [scriptPath, "--dry-run"], {
    cwd: repoRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      DISCORD_CODE_REVIEW_CHANNEL_ID: "1499430188105334997",
      GITHUB_EVENT_NAME: "pull_request",
      GITHUB_EVENT_PATH: eventPath,
      GITHUB_REF_NAME: "feature/contributor-guide",
      GITHUB_REPOSITORY: "Prompthon-IO/agent-systems-handbook",
      GITHUB_SHA: "abc123",
    },
  });

  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.equal(output.dryRun, true);
  assert.deepEqual(output.jobs, [
    {
      channelKey: "code-review",
      commitSha: "abc123",
      dedupeKey: "Prompthon-IO/agent-systems-handbook:pr:99:opened:code-review",
      discordChannelId: "1499430188105334997",
      eventType: "github_pull_request_opened",
      prNumber: 99,
      prTitle: "docs: add contributor guide",
      repoFullName: "Prompthon-IO/agent-systems-handbook",
      sourceUrl: "https://github.com/Prompthon-IO/agent-systems-handbook/pull/99",
    },
  ]);
});

test("release announcements target project announcements with release and handbook links", () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "discord-announcer-"));
  const eventPath = path.join(tempDir, "event.json");
  const releaseBodyPath = path.join(tempDir, "release-body.md");
  const releaseSha = "b18e895cf7a82d01c045cc8d4f5c28cceaa844f1";
  const releaseUrl = "https://github.com/Prompthon-IO/agent-systems-handbook/releases/tag/release-2026.05.04.1";

  writeJson(eventPath, {
    after: releaseSha,
    ref: "refs/heads/main",
    repository: {
      full_name: "Prompthon-IO/agent-systems-handbook",
      html_url: "https://github.com/Prompthon-IO/agent-systems-handbook",
    },
  });
  fs.writeFileSync(
    releaseBodyPath,
    [
      "## What's Changed",
      "* Add Coding Agents case study by @dprat0821 in #89",
      "* Refresh contributor onboarding by @outside-dev in #90",
      "* Polish navigation by @dprat0821 in #91",
      "",
      "## Full Changelog",
      "https://github.com/Prompthon-IO/agent-systems-handbook/compare/old...new",
    ].join("\n"),
  );

  const result = spawnSync(
    process.execPath,
    [scriptPath, "--release-announcement", "--dry-run"],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        ANNOUNCER_RELEASE_BODY_FILE: releaseBodyPath,
        ANNOUNCER_RELEASE_NAME: "release-2026.05.04.1",
        ANNOUNCER_RELEASE_TAG: "release-2026.05.04.1",
        ANNOUNCER_RELEASE_URL: releaseUrl,
        DISCORD_PROJECT_ANNOUNCEMENTS_CHANNEL_ID: "1499266299128184832",
        GITHUB_EVENT_NAME: "push",
        GITHUB_EVENT_PATH: eventPath,
        GITHUB_REF_NAME: "main",
        GITHUB_REPOSITORY: "Prompthon-IO/agent-systems-handbook",
        GITHUB_SHA: releaseSha,
        HANDBOOK_DEPLOYED_URL: "https://labs.prompthon.io",
      },
    },
  );

  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.equal(output.dryRun, true);
  assert.deepEqual(output.jobs, [
    {
      channelKey: "project-announcements",
      commitSha: releaseSha,
      dedupeKey: "Prompthon-IO/agent-systems-handbook:release:release-2026.05.04.1:project-announcements",
      discordChannelId: "1499266299128184832",
      eventType: "handbook_release_published",
      prNumber: null,
      prTitle: "release-2026.05.04.1",
      releaseContributors: ["dprat0821", "outside-dev"],
      repoFullName: "Prompthon-IO/agent-systems-handbook",
      sourceUrl: releaseUrl,
    },
  ]);
});
