#!/usr/bin/env python3
"""Validate a presentation-template manifest and write review artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
COLOR_ROLES = {
    "primary",
    "secondary",
    "accent",
    "background",
    "surface",
    "text",
    "muted",
}
TYPOGRAPHY_ROLES = {"heading", "body", "caption"}
PLACEHOLDER_KINDS = {
    "text",
    "rich-text",
    "image",
    "chart",
    "table",
    "metric",
    "date",
    "source",
    "logo",
}
ASSET_KINDS = {"logo", "image", "icon", "font"}
ASPECT_RATIOS = {"16:9", "4:3"}
SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path, label: str) -> tuple[dict[str, Any], list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [f"{label}: file does not exist: {path}"]
    except json.JSONDecodeError as exc:
        return {}, [f"{label}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    except OSError as exc:
        return {}, [f"{label}: could not read {path}: {exc}"]
    if not isinstance(value, dict):
        return {}, [f"{label}: top-level value must be an object"]
    return value, []


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_id(value: Any) -> bool:
    return non_empty_string(value) and bool(ID_PATTERN.fullmatch(value))


def validate_brief(brief: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("project_name", "audience", "purpose", "target_format"):
        if not non_empty_string(brief.get(field)):
            errors.append(f"brief.{field}: required non-empty string")

    requested = brief.get("requested_layouts")
    if requested is not None:
        if not isinstance(requested, list) or not requested:
            errors.append("brief.requested_layouts: must be a non-empty array when supplied")
        elif any(not valid_id(item) for item in requested):
            errors.append("brief.requested_layouts: every value must be a lowercase hyphen id")
        elif len(requested) != len(set(requested)):
            errors.append("brief.requested_layouts: duplicate layout ids are not allowed")

    tone = brief.get("tone")
    if tone is not None and (
        not isinstance(tone, list) or any(not non_empty_string(item) for item in tone)
    ):
        errors.append("brief.tone: must be an array of non-empty strings")

    constraints = brief.get("constraints")
    if constraints is not None and not isinstance(constraints, dict):
        errors.append("brief.constraints: must be an object")
    return errors


def validate_theme(theme: Any) -> list[str]:
    if not isinstance(theme, dict):
        return ["manifest.theme: required object"]

    errors: list[str] = []
    colors = theme.get("colors")
    if not isinstance(colors, dict):
        errors.append("manifest.theme.colors: required object")
    else:
        for role in sorted(COLOR_ROLES):
            value = colors.get(role)
            if not isinstance(value, str) or not HEX_PATTERN.fullmatch(value):
                errors.append(
                    f"manifest.theme.colors.{role}: required six-digit hex color"
                )

    typography = theme.get("typography")
    if not isinstance(typography, dict):
        errors.append("manifest.theme.typography: required object")
    else:
        for role in sorted(TYPOGRAPHY_ROLES):
            config = typography.get(role)
            if not isinstance(config, dict):
                errors.append(f"manifest.theme.typography.{role}: required object")
                continue
            if not non_empty_string(config.get("family")):
                errors.append(
                    f"manifest.theme.typography.{role}.family: required non-empty string"
                )
            size = config.get("size_pt")
            if isinstance(size, bool) or not isinstance(size, (int, float)) or size <= 0:
                errors.append(
                    f"manifest.theme.typography.{role}.size_pt: required positive number"
                )
    return errors


def validate_assets(assets: Any) -> list[str]:
    if not isinstance(assets, list):
        return ["manifest.assets: required array"]

    errors: list[str] = []
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        prefix = f"manifest.assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        asset_id = asset.get("id")
        if not valid_id(asset_id):
            errors.append(f"{prefix}.id: required lowercase hyphen id")
        elif asset_id in seen:
            errors.append(f"{prefix}.id: duplicate id {asset_id!r}")
        else:
            seen.add(asset_id)
        if asset.get("kind") not in ASSET_KINDS:
            errors.append(
                f"{prefix}.kind: must be one of {', '.join(sorted(ASSET_KINDS))}"
            )
        path = asset.get("path")
        if not non_empty_string(path):
            errors.append(f"{prefix}.path: required local path string")
        elif path.startswith(("http://", "https://", "data:")):
            errors.append(f"{prefix}.path: remote URLs and embedded data are not allowed")
        if not non_empty_string(asset.get("license_note")):
            errors.append(f"{prefix}.license_note: required permission or license note")
    return errors


def validate_layouts(layouts: Any) -> tuple[list[str], dict[str, dict[str, Any]]]:
    if not isinstance(layouts, list) or not layouts:
        return ["manifest.layouts: required non-empty array"], {}

    errors: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for index, layout in enumerate(layouts):
        prefix = f"manifest.layouts[{index}]"
        if not isinstance(layout, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        layout_id = layout.get("id")
        if not valid_id(layout_id):
            errors.append(f"{prefix}.id: required lowercase hyphen id")
        elif layout_id in by_id:
            errors.append(f"{prefix}.id: duplicate id {layout_id!r}")
        else:
            by_id[layout_id] = layout
        if not non_empty_string(layout.get("name")):
            errors.append(f"{prefix}.name: required non-empty string")
        if not non_empty_string(layout.get("usage_note")):
            errors.append(f"{prefix}.usage_note: required non-empty string")

        placeholders = layout.get("placeholders")
        if not isinstance(placeholders, list) or not placeholders:
            errors.append(f"{prefix}.placeholders: required non-empty array")
            continue
        placeholder_ids: set[str] = set()
        for placeholder_index, placeholder in enumerate(placeholders):
            item_prefix = f"{prefix}.placeholders[{placeholder_index}]"
            if not isinstance(placeholder, dict):
                errors.append(f"{item_prefix}: must be an object")
                continue
            placeholder_id = placeholder.get("id")
            if not valid_id(placeholder_id):
                errors.append(f"{item_prefix}.id: required lowercase hyphen id")
            elif placeholder_id in placeholder_ids:
                errors.append(f"{item_prefix}.id: duplicate id {placeholder_id!r}")
            else:
                placeholder_ids.add(placeholder_id)
            if placeholder.get("kind") not in PLACEHOLDER_KINDS:
                errors.append(
                    f"{item_prefix}.kind: must be one of "
                    f"{', '.join(sorted(PLACEHOLDER_KINDS))}"
                )
            if not isinstance(placeholder.get("required"), bool):
                errors.append(f"{item_prefix}.required: must be boolean")
            maximum = placeholder.get("max_characters")
            if maximum is not None and (
                isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0
            ):
                errors.append(f"{item_prefix}.max_characters: must be a positive integer")
    return errors, by_id


def validate_manifest(
    brief: dict[str, Any], manifest: dict[str, Any]
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    if manifest.get("schema_version") != "1.0":
        errors.append("manifest.schema_version: must be '1.0'")
    if not valid_id(manifest.get("template_id")):
        errors.append("manifest.template_id: required lowercase hyphen id")
    if not non_empty_string(manifest.get("name")):
        errors.append("manifest.name: required non-empty string")
    if manifest.get("aspect_ratio") not in ASPECT_RATIOS:
        errors.append("manifest.aspect_ratio: must be '16:9' or '4:3'")

    errors.extend(validate_theme(manifest.get("theme")))
    errors.extend(validate_assets(manifest.get("assets")))
    layout_errors, layouts_by_id = validate_layouts(manifest.get("layouts"))
    errors.extend(layout_errors)

    requested = brief.get("requested_layouts")
    if isinstance(requested, list):
        for layout_id in requested:
            if valid_id(layout_id) and layout_id not in layouts_by_id:
                errors.append(
                    f"brief.requested_layouts: unknown layout id {layout_id!r}"
                )
    return errors, layouts_by_id


def build_plan(
    brief: dict[str, Any],
    manifest: dict[str, Any],
    layouts_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    requested = brief.get("requested_layouts")
    selected_ids = requested if isinstance(requested, list) else list(layouts_by_id)
    inventory = []
    for position, layout_id in enumerate(selected_ids, start=1):
        layout = layouts_by_id[layout_id]
        inventory.append(
            {
                "order": position,
                "layout_id": layout_id,
                "name": layout["name"],
                "usage_note": layout["usage_note"],
                "placeholders": layout["placeholders"],
            }
        )
    return {
        "schema_version": "1.0",
        "project": {
            "name": brief["project_name"],
            "audience": brief["audience"],
            "purpose": brief["purpose"],
            "target_format": brief["target_format"],
            "tone": brief.get("tone", []),
            "constraints": brief.get("constraints", {}),
        },
        "template": {
            "template_id": manifest["template_id"],
            "name": manifest["name"],
            "aspect_ratio": manifest["aspect_ratio"],
            "theme": manifest["theme"],
            "assets": manifest["assets"],
        },
        "slide_inventory": inventory,
        "review_summary": {
            "layout_count": len(inventory),
            "asset_count": len(manifest["assets"]),
            "requires_external_upload": False,
        },
    }


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_review(plan: dict[str, Any]) -> str:
    project = plan["project"]
    template = plan["template"]
    lines = [
        f"# {project['name']} Template Review",
        "",
        "## Brief",
        "",
        f"- Audience: {project['audience']}",
        f"- Purpose: {project['purpose']}",
        f"- Target format: {project['target_format']}",
        f"- Tone: {', '.join(project['tone']) if project['tone'] else 'Not specified'}",
        "",
        "## Template",
        "",
        f"- Name: {template['name']}",
        f"- Id: `{template['template_id']}`",
        f"- Aspect ratio: {template['aspect_ratio']}",
        f"- Referenced local assets: {len(template['assets'])}",
        "",
        "## Layout Inventory",
        "",
        "| Order | Layout | Name | Best used for | Placeholders |",
        "| ---: | --- | --- | --- | ---: |",
    ]
    for item in plan["slide_inventory"]:
        lines.append(
            f"| {item['order']} | `{markdown_escape(item['layout_id'])}` | "
            f"{markdown_escape(item['name'])} | "
            f"{markdown_escape(item['usage_note'])} | "
            f"{len(item['placeholders'])} |"
        )
    lines.extend(
        [
            "",
            "## Review Boundary",
            "",
            "- This artifact validates structure; it is not a generated deck.",
            "- No asset was opened or uploaded.",
            "- Confirm the inventory before selecting a PPTX or Slides backend.",
            "- Visually inspect any generated deck for overflow, contrast, cropping, and hierarchy.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a presentation brief and template manifest."
    )
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--confirm")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    brief, errors = load_json(args.brief, "brief")
    manifest, manifest_load_errors = load_json(args.manifest, "manifest")
    errors.extend(manifest_load_errors)
    if not errors:
        errors.extend(validate_brief(brief))
        manifest_errors, layouts_by_id = validate_manifest(brief, manifest)
        errors.extend(manifest_errors)
    else:
        layouts_by_id = {}

    if errors:
        print("INVALID presentation template input", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    if args.validate_only:
        requested = brief.get("requested_layouts")
        count = len(requested) if isinstance(requested, list) else len(layouts_by_id)
        print(
            f"VALID template={manifest['template_id']} "
            f"layouts={len(layouts_by_id)} selected={count}"
        )
        return 0

    if args.output_dir is None:
        print("--output-dir is required unless --validate-only is used", file=sys.stderr)
        return 2
    if args.confirm != "GENERATE":
        print("Refusing to write output without --confirm GENERATE", file=sys.stderr)
        return 2

    output_dir = args.output_dir.expanduser().resolve()
    if output_dir == SKILL_ROOT or SKILL_ROOT in output_dir.parents:
        print("Refusing to write runtime output inside the skill package", file=sys.stderr)
        return 2

    plan_path = output_dir / "template-plan.json"
    review_path = output_dir / "template-review.md"
    existing = [path for path in (plan_path, review_path) if path.exists()]
    if existing and not args.force:
        joined = ", ".join(str(path) for path in existing)
        print(f"Refusing to overwrite existing output: {joined}", file=sys.stderr)
        return 2

    plan = build_plan(brief, manifest, layouts_by_id)
    review = build_review(plan)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    review_path.write_text(review, encoding="utf-8")
    print(f"WROTE {plan_path}")
    print(f"WROTE {review_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
