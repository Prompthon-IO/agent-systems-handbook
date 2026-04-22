# Contributing

This repository accepts more than one kind of public contribution.

The first question is not "article or code?" It is "what kind of artifact are
you adding?"

## Supported contribution types

- `lab article`: an evergreen page in `foundations/`, `patterns/`,
  `systems/`, `ecosystem/`, or `case-studies/`
- `radar note`: a short, time-scoped field update in `radar/`
- `source project`: a repo-owned example or starter under a lane-local
  `examples/` subpath
- `curated reference note`: a structured source map, roundup, or reading note
  under `contributor-kit/reference-notes/`

`publications/` is not a first-wave community contribution surface. Treat it as
an editorial extension area for mature lab pages.

## Start here

Use the matching guide before you draft anything:

- [Contributor Kit](./contributor-kit/README.md)
- [Article Guidelines](./contributor-kit/article-guidelines.md)
- [Radar Note Guidelines](./contributor-kit/radar-note-guidelines.md)
- [Source Project Guidelines](./contributor-kit/source-project-guidelines.md)
- [Reference Note Guidelines](./contributor-kit/reference-note-guidelines.md)
- [Review Checklist](./contributor-kit/review-checklist.md)

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

## Where each contribution belongs

- Lab articles live directly in the relevant lane folder.
- Radar notes live in `radar/`.
- Source projects live only in:
  - `patterns/examples/`
  - `systems/examples/`
  - `ecosystem/examples/`
  - `case-studies/examples/`
- Curated reference notes live in `contributor-kit/reference-notes/`.

Do not create `examples/` under `foundations/` in v1.
Do not add contributor-created material inside `references/`.

## Shared PR flow

1. Choose the contribution type.
2. Place the work in the correct folder using the matching template.
3. Add or update links from the relevant README.
4. Open a PR with a short scope summary.
5. Review the change against the shared checklist before requesting merge.

## Review standard

Every public contribution should pass the checks in
[Review Checklist](./contributor-kit/review-checklist.md):

- correct type and placement
- template completeness
- repo-native writing or structure
- safe attribution boundary
- useful cross-links
- clear status and maintenance expectations
