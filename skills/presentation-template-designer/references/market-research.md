# Presentation Template Toolchain Research

## Recommendation For The First Version

Use a local manifest-first workflow and keep the planning layer independent of
the rendering backend. Validate the manifest with the bundled standard-library
helper, then choose an editable backend:

1. Prefer `python-pptx` when adapting an existing PPTX or when a Python-local
   workflow is the simplest fit.
2. Prefer PptxGenJS when a JavaScript workflow is creating a new PPTX from
   explicit masters and reusable layouts.
3. Use the Google Slides API only when collaborative Slides output is a
   requirement and account authorization is explicit.
4. Reach for direct PresentationML only when a required feature cannot be
   preserved by the higher-level library.

This separation keeps brief intake, layout selection, privacy rules, and review
stable even when the output backend changes.

## Evidence Map

### python-pptx

- Official documentation:
  [Working with Presentations](https://python-pptx.readthedocs.io/en/stable/user/presentations.html)
  and
  [Presentation API](https://python-pptx.readthedocs.io/en/stable/api/presentation.html)
- The library opens a presentation through `Presentation()`, can start from an
  existing PPTX, exposes slides and shapes, and saves editable presentation
  output.
- Best fit here: local Python workflows and adaptation of a user-provided
  template whose theme, masters, and layouts already carry the visual system.
- Tradeoff: generation requires an additional Python dependency, so the bundled
  manifest validator stays dependency-free.

### PptxGenJS

- Official documentation: [PptxGenJS docs](https://gitbrent.github.io/PptxGenJS/docs/)
- The project provides a JavaScript API for editable PowerPoint output and
  reusable master-slide definitions.
- Best fit here: new programmatic PPTX generation inside an existing Node or
  TypeScript workflow.
- Tradeoff: it adds a Node dependency and a backend-specific layout layer.

### Google Slides API

- Official documentation:
  [Google Slides API overview](https://developers.google.com/slides/api/guides/overview)
- The API supports reading and updating presentations through service calls.
- Best fit here: a user explicitly requires collaborative Google Slides output
  in an authorized workspace.
- Tradeoff: OAuth, destination selection, network access, and external asset
  handling become part of the workflow. Keep these behind a separate approval.

### PresentationML And Open XML

- Official documentation:
  [Working with presentations](https://learn.microsoft.com/en-us/office/open-xml/presentation/)
- PresentationML exposes the package-level structure behind PPTX files.
- Best fit here: a narrow compatibility or preservation need that a high-level
  library cannot meet.
- Tradeoff: direct package editing has the highest implementation and validation
  burden. It should not be the default first version.

### Design-Canvas Services

Canva- or Figma-style workflows are useful when canvas-native collaboration and
visual handoff matter more than local PPTX automation. They are not the first
version here because uploads, workspace permissions, template ownership, and
export behavior introduce provider-specific boundaries. Use them only after the
user approves the service, account, destination, and asset handling.

### Markdown Or HTML Slides

Markdown-to-slides and HTML-to-slides can be deterministic for talks that do not
require native PowerPoint editing. They are a poor default for this issue because
the requested output is a reusable editable presentation template rather than a
single rendered talk.

## Decision Checklist

Choose the backend only after answering:

- Must the result be editable in PowerPoint, Google Slides, or a design canvas?
- Is there an existing template whose masters and layouts must be preserved?
- Is local-only processing required?
- Does the user authorize OAuth or asset upload?
- Which editable object types are required: text, images, tables, charts, or
  diagrams?
- How will the result be rendered and visually inspected?
