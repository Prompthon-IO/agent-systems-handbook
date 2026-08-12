---
name: presentation-template-designer
description: Plan reusable presentation templates from a creative brief, optional brand assets, or an existing deck. Use when Codex needs to define a slide inventory, choose an editable presentation toolchain, author or validate a template manifest, adapt a visual system for PowerPoint or Google Slides, or prepare a reviewed template plan before generating a deck.
---

# Presentation Template Designer

Read `README.md` first for the human-facing package story. This file is the
invocation contract for Codex.

## Core Boundary

Plan before generating. Produce a reviewed slide inventory and template
manifest before creating a deck or uploading assets to a third-party service.
The bundled helper validates that plan and writes deterministic review
artifacts; it does not upload files or silently generate a deck.

## Required Inputs

Collect:

- purpose and intended use
- audience
- target format, such as editable PPTX or Google Slides
- desired tone or visual direction
- required layout types or approximate slide count

Optional inputs:

- color palette and typography preferences
- local paths to logos or brand assets
- an existing presentation or template to adapt
- content constraints, accessibility needs, and licensing notes

Ask no more than three focused questions at a time. If the user supplies enough
information, make explicit assumptions and continue.

## Workflow

1. **Frame the brief.** Confirm the audience, purpose, target format, tone,
   layout needs, and constraints. Keep private asset paths local.
2. **Choose a toolchain.** Read `references/market-research.md` when the
   generation backend is not already selected. Default to a local editable
   workflow; use a connected design service only with explicit authorization.
3. **Draft the inventory.** Read `references/layout-catalog.md`, select the
   smallest useful set of layouts, and explain when each should be used.
4. **Review with the user.** Present the proposed story structure, layouts,
   theme direction, and important assumptions. Revise until the user approves
   the inventory.
5. **Write the manifest.** Follow
   `references/template-manifest-schema.md`. Store asset paths and licensing
   notes, not embedded private files.
6. **Validate first.** Run the bundled helper with `--validate-only`.
7. **Generate review artifacts.** After the user approves the plan, run the
   helper with `--confirm GENERATE`. Review the normalized JSON and Markdown
   inventory before starting a PPTX or Slides generation task.
8. **Generate in the selected backend.** Keep editable text and shapes. Reuse an
   existing local template when supplied. Treat any upload, OAuth consent, or
   publication as a separate user-authorized action.
9. **Inspect visually.** Render or open the resulting deck and check overflow,
   contrast, spacing, cropping, hierarchy, and layout coverage.

## Toolchain Selection

- Choose **python-pptx** when the work is local, Python is preferred, or an
  existing PPTX template and its layouts should be reused.
- Choose **PptxGenJS** when generating a new editable PPTX from a JavaScript
  workflow with explicit master layouts.
- Choose the **Google Slides API** when collaborative Slides output is required
  and the user has explicitly authorized the account and destination.
- Use direct **PresentationML/OOXML** manipulation only for a required feature
  the higher-level library cannot preserve.
- Use a Canva- or Figma-style workflow only when editable design-canvas output
  materially matters and the user approves external asset handling.

Read `references/market-research.md` for evidence and tradeoffs.

## Commands

Resolve paths relative to this skill directory.

Validate the bundled example without writing output:

```bash
python3 scripts/generate_sample_template.py \
  --brief examples/brief.json \
  --manifest examples/template-manifest.json \
  --validate-only
```

Generate a normalized plan and review report:

```bash
python3 scripts/generate_sample_template.py \
  --brief examples/brief.json \
  --manifest examples/template-manifest.json \
  --output-dir /tmp/presentation-template-review \
  --confirm GENERATE
```

The output directory contains:

```text
template-plan.json
template-review.md
```

The helper refuses to overwrite either file unless `--force` is supplied.

## Safety And Privacy

- Never commit user logos, proprietary templates, unreleased decks, or generated
  runtime output.
- Never upload assets or decks to an external service without explicit user
  authorization for that service and destination.
- Record a license or permission note for fonts, icons, stock assets, and
  template inspiration before using them.
- Keep secrets, OAuth tokens, personal data, speaker notes, and revision history
  out of manifests and examples.
- Prefer editable text, shapes, tables, and charts. Do not flatten whole slides
  into images unless the user explicitly requests static output.
- Never overwrite an existing user deck. Write to a new output path and show the
  user what was created.
- Treat signing in, OAuth consent, publishing, and paid-template acquisition as
  separate approval boundaries.

## Review Checklist

Before calling a template ready:

- the audience, purpose, and target format are explicit
- the user approved the slide inventory
- every layout has a unique id, usage note, and placeholders
- theme colors and typography roles are complete
- private assets remain local and licensing notes are present
- the manifest passes the bundled validator
- the generated deck remains editable
- a visual pass found no overflow, clipping, low contrast, or accidental
  disclosure

## Response Pattern

Report:

- assumptions and unresolved choices
- selected toolchain and why
- approved layout inventory
- manifest and review-artifact paths
- validation results
- any external authorization still required
- the next action: revise the plan, generate an editable deck, or visually
  review an existing result
