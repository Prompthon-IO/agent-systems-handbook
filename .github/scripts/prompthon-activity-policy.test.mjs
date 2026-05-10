import assert from "node:assert/strict";
import test from "node:test";

import {
  extractTrackFromLabels,
  extractWorkKindFromLabels,
  findLinkedIssueNumbers,
  labelsForIssueBody,
  validateChangedFilesForTrack,
} from "./prompthon-activity-policy.mjs";

test("extracts track and work kind labels", () => {
  const labels = [
    { name: "track: builder" },
    { name: "kind: feature" },
    { name: "status: pending-review" },
  ];
  assert.equal(extractTrackFromLabels(labels), "builder");
  assert.equal(extractWorkKindFromLabels(labels), "feature");
});

test("maps issue-form fields to activity labels", () => {
  const body = [
    "### Contribution track",
    "",
    "Explorer",
    "",
    "### Work kind",
    "",
    "Radar note",
    "",
    "### Proposed content change",
    "",
    "Add a radar note.",
  ].join("\n");

  assert.deepEqual(labelsForIssueBody(body), [
    "status: pending-review",
    "track: explorer",
    "kind: radar-note",
  ]);
});

test("finds linked issue numbers from closing keywords", () => {
  assert.deepEqual(
    findLinkedIssueNumbers("Closes #12\n\nFixes #13 and resolves #12."),
    [12, 13],
  );
});

test("validates explorer path policy", () => {
  assert.deepEqual(
    validateChangedFilesForTrack("explorer", [
      "foundations/the-agent-system.mdx",
      "scripts/check_filename_casing.py",
    ]),
    {
      allowedPaths: [
        "foundations/",
        "patterns/",
        "ecosystem/",
        "case-studies/",
        "radar/",
        "reading-paths/",
        "contributor-kit/reference-notes/",
        "publications/",
        "zh-Hans/",
      ],
      invalidFiles: ["scripts/check_filename_casing.py"],
      valid: false,
    },
  );
});

test("validates practitioner and builder path policy", () => {
  assert.equal(
    validateChangedFilesForTrack("practitioner", [
      "skills/daily-news-watcher/SKILL.md",
      "workshops/index.mdx",
    ]).valid,
    true,
  );
  assert.equal(
    validateChangedFilesForTrack("builder", [
      ".github/workflows/prompthon-track-guard.yml",
      "systems/context-engineering.mdx",
    ]).valid,
    true,
  );
});
