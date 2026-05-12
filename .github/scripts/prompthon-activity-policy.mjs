export const TRACKS = ["explorer", "practitioner", "builder"];

export const WORK_KINDS = [
  "article",
  "radar-note",
  "case-study",
  "reference-note",
  "reading-path",
  "translation",
  "workflow",
  "prompt",
  "template",
  "skill-package",
  "tool-showcase",
  "workshop-material",
  "bug",
  "bug-fix",
  "feature",
  "demo",
  "docs",
  "test",
  "ci",
  "script",
  "enhancement",
];

export const STATUS_LABELS = [
  "pending-review",
  "approved",
  "rejected",
  "claimed",
  "in-progress",
  "pr-submitted",
  "completed",
  "expired",
];

export const TRACK_ALLOWED_PATHS = {
  explorer: [
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
  practitioner: [
    "skills/",
    "snippets/",
    "workshops/",
    "templates/",
  ],
  builder: [
    "scripts/",
    "githooks/",
    ".github/",
    "examples/",
    "systems/",
    "src/",
    "apps/",
    "packages/",
  ],
};

export function normalizeChoice(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/`/g, "")
    .replace(/\s+/g, "-");
}

export function extractLabelNames(labels) {
  return (labels || [])
    .map((label) => typeof label === "string" ? label : label?.name)
    .filter(Boolean);
}

function valueAfterPrefix(label, prefix) {
  const normalized = String(label || "").trim().toLowerCase();
  if (!normalized.startsWith(prefix)) {
    return null;
  }
  return normalized.slice(prefix.length).trim();
}

export function extractTrackFromLabels(labels) {
  for (const label of extractLabelNames(labels)) {
    const value = valueAfterPrefix(label, "track:");
    if (TRACKS.includes(value)) {
      return value;
    }
  }
  return null;
}

export function extractWorkKindFromLabels(labels) {
  for (const label of extractLabelNames(labels)) {
    const value = valueAfterPrefix(label, "kind:");
    if (WORK_KINDS.includes(value)) {
      return value;
    }
  }
  return null;
}

export function extractIssueFormValue(body, heading) {
  const lines = String(body || "").split(/\r?\n/);
  const headingLine = `### ${heading}`;
  const start = lines.findIndex((line) => line.trim() === headingLine);
  if (start < 0) {
    return null;
  }

  const valueLines = [];
  for (const line of lines.slice(start + 1)) {
    if (line.startsWith("### ")) {
      break;
    }
    const trimmed = line.trim();
    if (!trimmed || trimmed === "_No response_") {
      continue;
    }
    valueLines.push(trimmed);
  }
  return valueLines.length ? valueLines.join("\n").trim() : null;
}

export function labelsForIssueBody(body) {
  const track = normalizeChoice(
    extractIssueFormValue(body, "Contribution track") ||
    extractIssueFormValue(body, "Track"),
  );
  const workKind = normalizeChoice(
    extractIssueFormValue(body, "Work kind") ||
    extractIssueFormValue(body, "Kind"),
  );

  const labels = ["status: pending-review"];
  if (TRACKS.includes(track)) {
    labels.push(`track: ${track}`);
  }
  if (WORK_KINDS.includes(workKind)) {
    labels.push(`kind: ${workKind}`);
  }
  return labels;
}

export function findLinkedIssueNumbers(text) {
  const numbers = [];
  const pattern = /\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b/gi;
  let match = pattern.exec(String(text || ""));
  while (match) {
    numbers.push(Number.parseInt(match[1], 10));
    match = pattern.exec(String(text || ""));
  }
  return [...new Set(numbers.filter(Number.isInteger))];
}

export function validateChangedFilesForTrack(track, changedFiles, pathPolicy = TRACK_ALLOWED_PATHS) {
  const allowedPaths = pathPolicy[track] || [];
  const invalidFiles = changedFiles.filter((filePath) =>
    !allowedPaths.some((allowedPath) => filePath.startsWith(allowedPath)),
  );
  return {
    allowedPaths,
    invalidFiles,
    valid: invalidFiles.length === 0,
  };
}
