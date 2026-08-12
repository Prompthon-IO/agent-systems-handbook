# Template Manifest Schema

The manifest is the portable contract between planning and generation. Keep it
JSON so it can be validated before a backend is selected.

## Top-Level Shape

```json
{
  "schema_version": "1.0",
  "template_id": "workshop-clear-light",
  "name": "Workshop Clear Light",
  "aspect_ratio": "16:9",
  "theme": {},
  "assets": [],
  "layouts": []
}
```

Required fields:

- `schema_version`: currently `"1.0"`
- `template_id`: lowercase letters, numbers, and hyphens
- `name`: human-facing template name
- `aspect_ratio`: `"16:9"` or `"4:3"`
- `theme`: color and typography roles
- `assets`: local references and permission notes; may be empty
- `layouts`: one or more reusable layout definitions

## Theme

```json
{
  "colors": {
    "primary": "#2457C5",
    "secondary": "#5B6B8C",
    "accent": "#20A37A",
    "background": "#F7F9FC",
    "surface": "#FFFFFF",
    "text": "#172033",
    "muted": "#667085"
  },
  "typography": {
    "heading": {"family": "Aptos Display", "size_pt": 30},
    "body": {"family": "Aptos", "size_pt": 18},
    "caption": {"family": "Aptos", "size_pt": 11}
  }
}
```

All seven color roles are required and must be six-digit hex values. All three
typography roles are required. Font family is a name, not a bundled font file;
record permission before distributing a non-system font.

## Assets

```json
{
  "id": "brand-logo",
  "kind": "logo",
  "path": "/local/path/logo.svg",
  "license_note": "Provided by the user for this project"
}
```

- Keep `path` local.
- Do not embed base64 data, tokens, or private binary files in the manifest.
- `kind` is `logo`, `image`, `icon`, or `font`.
- `license_note` is required for every asset.

## Layouts

```json
{
  "id": "comparison",
  "name": "Side-by-side comparison",
  "usage_note": "Compare two options using the same criteria.",
  "placeholders": [
    {"id": "title", "kind": "text", "required": true, "max_characters": 70},
    {"id": "left", "kind": "rich-text", "required": true, "max_characters": 260},
    {"id": "right", "kind": "rich-text", "required": true, "max_characters": 260},
    {"id": "source", "kind": "source", "required": false, "max_characters": 160}
  ]
}
```

Rules:

- layout and placeholder ids must be unique lowercase hyphen ids
- `name` and `usage_note` must be non-empty
- every layout has at least one placeholder
- `kind` uses a value from `references/layout-catalog.md`
- `required` is boolean
- `max_characters`, when supplied, is a positive integer

## Brief Linkage

The brief may contain `requested_layouts`. Every requested id must exist in
the manifest. The helper copies those layouts into the generated slide
inventory in the requested order. If the field is omitted, all manifest layouts
are included.

## Validation Boundary

The bundled helper validates structure and cross-references. It does not:

- open local assets
- verify font installation
- upload anything
- assess visual quality
- guarantee that a backend preserves every object

After backend generation, render the deck and perform a visual inspection.
