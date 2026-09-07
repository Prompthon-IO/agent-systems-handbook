import { TRACKS, WORK_KINDS, extractLabelNames } from "./prompthon-activity-policy.mjs";

// Treat the body as data. Examples, hidden comments and prose never select labels.
export function classificationChoices(body, heading) {
  const clean = String(body || "").replace(/<!--[\s\S]*?-->/g, "")
    .replace(/^(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\1[^\n]*$/gm, "");
  const sections = clean.split(/^## /m).slice(1).filter(s => s.split(/\r?\n/)[0].trim() === heading);
  if (sections.length > 1) throw new Error(`Keep only one "${heading}" section in the PR description.`);
  return (sections[0] || "").split(/\r?\n/).flatMap(line => {
    const checked = line.match(/^\s*[-*] \[x\]\s+(.+)$/i);
    if (!checked) return [];
    const value = checked[1].match(/^`([a-z-]+)`(?:\s|$)/);
    if (!value) throw new Error(`Use the template's backtick value in "${heading}"; do not rename the option.`);
    return [value[1]];
  });
}

export function resolveClassification({ body, labels = [], issues = [] }) {
  const result = {};
  for (const [key, heading, allowed] of [["track", "Repository track", TRACKS], ["kind", "Work kind", WORK_KINDS]]) {
    const sources = [
      ["PR labels", extractLabelNames(labels).filter(x => x.toLowerCase().startsWith(key + ":")).map(x => x.slice(key.length + 1).trim().toLowerCase())],
      ...issues.map(issue => [`Issue #${issue.number}`, extractLabelNames(issue.labels).filter(x => x.toLowerCase().startsWith(key + ":")).map(x => x.slice(key.length + 1).trim().toLowerCase())]),
      ["PR selection", classificationChoices(body, heading)],
    ];
    for (const [name, values] of sources) {
      if (values.length > 1) throw new Error(`${name}: select exactly one ${key}; multiple values are not allowed.`);
      if (values.some(x => !allowed.includes(x))) throw new Error(`${name}: unknown ${key}. Allowed values: ${allowed.join(", ")}.`);
    }
    const selected = sources.filter(([, values]) => values.length);
    const values = [...new Set(selected.flatMap(([, values]) => values))];
    if (values.length > 1) throw new Error(`${key} conflict: ${selected.map(([name, values]) => `${name}=${values[0]}`).join("; ")}. Align the PR selection with the linked Issue. Ask a maintainer to correct an existing label if necessary.`);
    if (!values.length) throw new Error(`Missing ${key}. In the PR description, select one checkbox under "${heading}", or link an Issue with a ${key}: label using Closes #123. You do not need permission to manage labels.`);
    result[key] = values[0];
  }
  return { ...result, labels: [`track: ${result.track}`, `kind: ${result.kind}`] };
}
