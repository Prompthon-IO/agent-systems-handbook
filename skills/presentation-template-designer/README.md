# Presentation Template Designer

## Why This Skill Exists

A reusable presentation template is more than a color palette. It needs a
coherent set of layouts, clear placeholder roles, typography and spacing rules,
and guidance about when each slide pattern should be used.

This package turns a short creative brief into a reviewable template plan before
generation begins. The user can refine the story, layout inventory, and visual
direction while changes are still inexpensive. A deterministic helper then
validates the manifest and produces a normalized plan plus a Markdown review
report.

## Who It Is For

Use this package when a student, facilitator, operator, or designer wants to:

- create an editable presentation template from a short brand or style brief
- adapt an existing presentation to a new topic or visual direction
- agree on the slide inventory before generating a full deck
- compare local PPTX generation with a collaborative Slides workflow
- document color, typography, assets, placeholders, and layout usage in a
  portable manifest

## End-To-End Workflow

1. **Brief intake.** Capture the purpose, audience, target format, tone,
   approximate slide count, required layouts, and optional local brand assets.
2. **Toolchain decision.** Choose a local editable backend by default. Move to a
   connected design service only when collaboration or canvas-native editing
   justifies the authorization and upload boundary.
3. **Inventory review.** Select layouts from
   `references/layout-catalog.md` and review the proposed story structure with
   the user.
4. **Manifest authoring.** Record the theme, typography, assets, layouts,
   placeholders, and usage notes using
   `references/template-manifest-schema.md`.
5. **Deterministic validation.** Run
   `scripts/generate_sample_template.py --validate-only`.
6. **Review-artifact generation.** After approval, run the helper with
   `--confirm GENERATE` to create `template-plan.json` and
   `template-review.md` in a user-named output directory.
7. **Deck generation and visual QA.** Use the selected PPTX or Slides backend,
   preserve editable objects, and inspect the rendered result for overflow,
   contrast, spacing, cropping, and hierarchy.

## What The Helper Does

The helper uses only Python's standard library. It:

- validates the example brief and manifest
- checks color tokens, typography roles, layout ids, usage notes, placeholders,
  and requested-layout references
- writes a normalized template plan
- writes a Markdown inventory for human review
- refuses to overwrite existing output unless `--force` is explicit

It intentionally does not upload assets, call an image model, authenticate to a
design service, or generate a PPTX by itself. Those actions depend on the
approved backend and may require separate user authorization.

## Package Map

- `SKILL.md`: Codex workflow and safety contract
- `references/layout-catalog.md`: common reusable layouts and suitability notes
- `references/market-research.md`: official-source-backed toolchain comparison
- `references/template-manifest-schema.md`: manifest contract and validation rules
- `examples/brief.json`: realistic workshop-template brief
- `examples/template-manifest.json`: complete example manifest
- `scripts/generate_sample_template.py`: validator and review-artifact generator

## Privacy And Licensing Boundary

Do not commit private logos, brand files, proprietary templates, unreleased
decks, or generated runtime output. Keep asset references local, record license
or permission notes, and require explicit authorization before sending anything
to a third-party design service.
