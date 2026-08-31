# Source notes

- Upstream project: anthropics/knowledge-work-plugins
- Exact source URL: https://github.com/anthropics/knowledge-work-plugins/blob/8c3ec5534fc6948b461c6a0275bdfdb8ab0c9888/operations/skills/process-optimization/SKILL.md
- Commit reviewed: `8c3ec5534fc6948b461c6a0275bdfdb8ab0c9888`
- Repository license: Apache-2.0; where unverified, no copying permission is inferred.
- Copied: no external prose, scripts, diagrams or assets.
- Rewritten: original Prompthon workflow and deterministic helper.
- Prompthon modifications: Define and run ordered, repeatable tool workflows, stopping at approval gates and recording each step. Delegate classification and synthesis to their own skills. Shared scoped persistence, classroom fixtures, privacy/approval gates, canonical readback and reset guidance.
- Date reviewed: 2026-08-30.

Internal baseline: existing Handbook skills at commit `4103082479cfe632b4ad0def86955f89ef1398e5`. Existing organizer classification and knowledge extractors are reused by import, not replaced. Automate invokes them without reimplementing their jobs. See the [shared audit](../../course-support/references/source-audit.json).
