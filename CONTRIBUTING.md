# Contributing

This repository accepts more than one kind of public contribution to Prompthon Agentic Labs.

The first question is not "article or code?" It is "what kind of artifact are
you adding?"

## Supported contribution types

- `lab article`: an evergreen page in `foundations/`, `patterns/`,
  `systems/`, `ecosystem/`, or `case-studies/`
- `radar note`: a short, time-scoped field update in `radar/`
- `source project`: a repo-owned example or starter under a lane-local
  `examples/` subpath
- `practitioner skill package`: a Codex-compatible package under `skills/`
  that can include `SKILL.md`, agent metadata, helper scripts, reference files,
  and the minimum documentation needed to run or review the package
- `curated reference note`: a structured source map, roundup, or reading note
  under `contributor-kit/reference-notes/`

`publications/` is not a first-wave community contribution surface. Treat it as
an editorial extension area for mature lab pages.

## Start here

Use the matching guide before you draft anything:

- [Contributor Kit](./contributor-kit/index.mdx)
- [Basic GitHub Flow For Contributors](./contributor-kit/contribution-workflow.mdx)
- [GitHub Issue Guide](./contributor-kit/github-issue-guide.mdx)
- [Practitioner Skills](./skills/index.mdx)
- [Article Guidelines](./contributor-kit/article-guidelines.mdx)
- [Radar Note Guidelines](./contributor-kit/radar-note-guidelines.mdx)
- [Source Project Guidelines](./contributor-kit/source-project-guidelines.mdx)
- [Reference Note Guidelines](./contributor-kit/reference-note-guidelines.mdx)
- [Review Checklist](./contributor-kit/review-checklist.mdx)

## Shared working rules

- Keep public content repo-native. Use imported material under `references/` as
  source input, not as publishable copy.
- Do not copy upstream prose, screenshots, diagrams, or large code surfaces
  into tracked public paths.
- Pick the correct lane or contribution type before writing.
- Follow the matching template rather than inventing a custom format.
- Link your contribution from the relevant lane README or contributor surface so
  it is discoverable.
- Document source lineage whenever external material shaped the contribution.

## Recommended local checks

Install the shared Git hooks before pushing from a case-insensitive filesystem:

```bash
git config core.hooksPath githooks
```

The current `pre-push` hook runs:

```bash
python3 scripts/check_filename_casing.py
```

This blocks pushes when tracked paths differ only by case or when the Git index
path casing no longer matches the working tree casing.

## Where each contribution belongs

- Lab articles live directly in the relevant lane folder.
- Radar notes live in `radar/`.
- Source projects live only in:
  - `patterns/examples/`
  - `systems/examples/`
  - `ecosystem/examples/`
  - `case-studies/examples/`
- Practitioner skill packages live in `skills/<skill-slug>/`. They may include
  instructions, configuration, deterministic helper code, and rule/reference
  files as one reviewable package.
- Curated reference notes live in `contributor-kit/reference-notes/`.

Do not create `examples/` under `foundations/` in v1.
Do not add contributor-created material inside `references/`.

## Issue intake

Use [GitHub Issue Guide](./contributor-kit/github-issue-guide.mdx) before filing
an issue. It explains which repository issue form to use for content proposals,
source-project proposals, practitioner skill packages, repository feature
requests, process changes, and bugs.

If you are still deciding whether the request belongs in Discord or GitHub, use
[Basic GitHub Flow For Contributors](./contributor-kit/contribution-workflow.mdx)
for the routing sequence.

## Shared PR flow

1. Choose the contribution type.
2. Find or open the issue that defines the work.
3. Claim the issue with a visible comment and wait for maintainer
   acknowledgement or the `claimed` label.
4. Fork the repository if you do not have write access, or create a focused
   branch from the latest `develop` if you do.
5. Place the work in the correct folder using the matching template.
6. Add or update links from the relevant README or contributor surface.
7. Open a PR into `develop` with a short scope summary and the linked issue.
8. Review the change against the shared checklist before requesting merge.

## Branch and release flow

`develop` is the shared integration branch for normal contributor work. Use it
for lab articles, radar notes, source projects, practitioner skill packages,
reference notes, and repository process changes.

`main` is the production Mintlify branch. Merges into `main` are release events,
and they trigger production publishing plus a GitHub release/tag. Do not open
feature or content PRs directly into `main`.

Release PRs into `main` are opened only by `dprat0821` from the same-repository
`develop` branch. This keeps deployment authorization and release tagging under
one maintainer account while still allowing contributors to collaborate through
`develop`.

## Review standard

Every public contribution should pass the checks in
[Review Checklist](./contributor-kit/review-checklist.mdx):

- correct type and placement
- template completeness
- repo-native writing or structure
- safe attribution boundary
- useful cross-links
- clear status and maintenance expectations
