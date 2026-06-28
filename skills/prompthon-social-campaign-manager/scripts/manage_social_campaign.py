#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = os.environ.get(
    "PROMPTHON_SOCIAL_BASE_URL", "https://agents.prompthon.io"
)
DEFAULT_ORG_ID = os.environ.get("PROMPTHON_SOCIAL_ORG_ID", "")
DEFAULT_BRIDGE_TOKEN = os.environ.get("PROMPTHON_SOCIAL_BRIDGE_TOKEN", "")


class ApiError(RuntimeError):
    pass


def read_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def dump_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=True)
    sys.stdout.write("\n")


def join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def resolve_optional_body(
    body_file: str | None, body_json: str | None, require_body: bool = False
) -> Any | None:
    if body_file:
        return read_json_file(body_file)
    if body_json:
        return json.loads(body_json)
    if require_body:
        raise ApiError("Provide --body-file or --body-json.")
    return None


def build_auth_headers(args: argparse.Namespace) -> dict[str, str]:
    headers: dict[str, str] = {}
    auth_mode = getattr(args, "auth_mode", "none")
    if auth_mode == "local-bypass":
        headers["x-prompthon-local-auth-bypass"] = "1"
    elif auth_mode == "bridge-token":
        token = getattr(args, "bridge_token", "") or DEFAULT_BRIDGE_TOKEN
        if not token:
            raise ApiError(
                "bridge-token auth requires --bridge-token or PROMPTHON_SOCIAL_BRIDGE_TOKEN."
            )
        headers["x-prompthon-local-bridge-token"] = token
    return headers


def request_json(
    url: str,
    method: str,
    headers: dict[str, str] | None = None,
    body: Any | None = None,
) -> Any:
    encoded = None
    prepared_headers = dict(headers or {})
    if body is not None:
        prepared_headers["Content-Type"] = "application/json"
        encoded = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=encoded,
        headers=prepared_headers,
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        payload = None
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = None
        detail = payload.get("error") if isinstance(payload, dict) else raw
        raise ApiError(f"{method.upper()} {url} failed: {error.code} {detail}") from error
    except urllib.error.URLError as error:
        raise ApiError(f"{method.upper()} {url} failed: {error.reason}") from error


def social_api_request(
    args: argparse.Namespace,
    method: str,
    path: str,
    body: Any | None = None,
) -> Any:
    org_id = getattr(args, "org_id", "") or DEFAULT_ORG_ID
    if not org_id:
        raise ApiError("--org-id or PROMPTHON_SOCIAL_ORG_ID is required.")
    base_url = getattr(args, "base_url", "") or DEFAULT_BASE_URL
    headers = build_auth_headers(args)
    url = join_url(base_url, f"/api/organizations/{org_id}/social/{path}")
    payload = request_json(url, method, headers=headers, body=body)
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ApiError(f"{method.upper()} {path} did not return a success envelope.")
    return payload.get("data")


def command_exchange_handoff(args: argparse.Namespace) -> None:
    base_url = args.base_url or DEFAULT_BASE_URL
    url = join_url(base_url, "/api/agents/local-bridge/exchange")
    payload = request_json(
        url,
        "POST",
        body={
            "code": args.code,
            "bridgeOrigin": args.bridge_origin,
        },
    )
    dump_json(payload)


def command_request(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json)
    data = social_api_request(args, args.method, args.path, body)
    dump_json(data)


def command_list_channels(args: argparse.Namespace) -> None:
    dump_json(social_api_request(args, "GET", "channels"))


def command_list_campaigns(args: argparse.Namespace) -> None:
    dump_json(social_api_request(args, "GET", "campaigns"))


def command_list_posts(args: argparse.Namespace) -> None:
    dump_json(social_api_request(args, "GET", "posts"))


def command_get_post(args: argparse.Namespace) -> None:
    dump_json(social_api_request(args, "GET", f"posts/{args.post_id}"))


def command_create_campaign(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json, require_body=True)
    dump_json(social_api_request(args, "POST", "campaigns", body))


def command_update_campaign(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json, require_body=True)
    dump_json(social_api_request(args, "PATCH", f"campaigns/{args.campaign_id}", body))


def command_create_post(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json, require_body=True)
    dump_json(social_api_request(args, "POST", "posts", body))


def command_update_post(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json, require_body=True)
    dump_json(social_api_request(args, "PATCH", f"posts/{args.post_id}", body))


def command_schedule_post(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json)
    if body is None:
        body = {
            "publishAt": args.publish_at,
            "postState": args.post_state,
            "settings": {
                "timezone": args.timezone,
            },
        }
    dump_json(social_api_request(args, "POST", f"posts/{args.post_id}/schedule", body))


def command_search_media(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json)
    if body is None:
        body = {
            "query": args.query,
            "limit": args.limit,
            "perProvider": args.per_provider,
            "orientation": args.orientation,
            "providers": args.providers,
        }
    dump_json(social_api_request(args, "POST", "media/search", body))


def command_attach_media(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json)
    if body is None:
        body = build_media_attach_body_from_args(args)
    dump_json(social_api_request(args, "POST", f"posts/{args.post_id}/media", body))


def command_rewrite_post(args: argparse.Namespace) -> None:
    body = resolve_optional_body(args.body_file, args.body_json)
    if body is None:
        body = {"tone": args.tone}
        if args.selection_file:
            body["selection"] = read_json_file(args.selection_file)
        if args.editor_context_file:
            body["editorContext"] = read_json_file(args.editor_context_file)
    dump_json(social_api_request(args, "POST", f"posts/{args.post_id}/ai-rewrite", body))


def apply_selection_rewrite(input_context: dict[str, Any], replacement_text: str) -> str:
    content = str(input_context.get("content") or "")
    selection = input_context.get("selection")
    if not isinstance(selection, dict):
        raise ApiError("Editor context is missing a selection object.")
    start = selection.get("start")
    end = selection.get("end")
    selected_text = selection.get("selectedText")
    prefix_text = selection.get("prefixText") or ""
    suffix_text = selection.get("suffixText") or ""
    if not isinstance(start, int) or not isinstance(end, int):
        raise ApiError("Selection start and end must be integers.")
    if not isinstance(selected_text, str):
        raise ApiError("Selection selectedText must be a string.")

    before = content[:start]
    current_selection = content[start:end]
    after = content[end:]
    if current_selection == selected_text:
        return f"{before}{replacement_text}{after}"

    exact_window_match = f"{prefix_text}{selected_text}{suffix_text}"
    current_window = content[max(0, start - len(prefix_text)) : min(len(content), end + len(suffix_text))]
    if current_window == exact_window_match:
        return f"{before}{replacement_text}{after}"

    fallback_needle = f"{prefix_text}{selected_text}{suffix_text}"
    fallback_index = content.find(fallback_needle) if (prefix_text or suffix_text) else -1
    if fallback_index >= 0:
        selected_start = fallback_index + len(prefix_text)
        selected_end = selected_start + len(selected_text)
        return f"{content[:selected_start]}{replacement_text}{content[selected_end:]}"

    raise ApiError(
        "The selected text no longer matches the current post content. Refresh the editor context and try again."
    )


def command_replace_selection(args: argparse.Namespace) -> None:
    editor_context = read_json_file(args.editor_context_file)
    if not isinstance(editor_context, dict):
        raise ApiError("Editor context file must contain an object.")
    if editor_context.get("kind") != "social_post_content_editor":
        raise ApiError("Editor context kind must be social_post_content_editor.")
    post_id = args.post_id or editor_context.get("postId")
    if not isinstance(post_id, str) or not post_id:
        raise ApiError("Provide --post-id or include postId in the editor context.")
    replacement_text = args.replacement_text
    if args.replacement_file:
        replacement_text = read_text_file(args.replacement_file)
    if replacement_text is None:
        raise ApiError("Provide --replacement-text or --replacement-file.")

    rewritten = apply_selection_rewrite(editor_context, replacement_text)
    patch_payload = {
        "rawIdea": rewritten,
    }
    if args.post_state:
        patch_payload["postState"] = args.post_state

    post = social_api_request(args, "PATCH", f"posts/{post_id}", patch_payload)
    dump_json(
        {
            "post": post,
            "updatedContent": rewritten,
        }
    )


def build_plan_settings(post: dict[str, Any]) -> dict[str, Any]:
    providers = list(post.get("providers") or [])
    hashtags = list(post.get("hashtags") or [])
    settings: dict[str, Any] = {
        "timezone": post.get("timezone", "America/Toronto"),
        "publishAt": post.get("publishAt"),
        "targetChannels": providers,
        "hashtags": hashtags,
    }
    if post.get("firstComment"):
        settings["firstComment"] = post["firstComment"]
    if post.get("altText"):
        settings["altText"] = post["altText"]
    return settings


def build_variant_overrides(post: dict[str, Any], settings: dict[str, Any]) -> list[dict[str, Any]]:
    copy_text = str(post.get("copy", ""))
    metadata = dict(post.get("metadata") or {})
    provider_copy = post.get("providerCopy") or {}
    providers = list(post.get("providers") or [])
    overrides = []
    for provider in providers:
        provider_specific_copy = str(provider_copy.get(provider, copy_text))
        overrides.append(
            {
                "provider": provider,
                "copyText": provider_specific_copy,
                "metadata": {
                    **metadata,
                    "mirroredCopy": provider_specific_copy == copy_text,
                    "settings": settings,
                },
            }
        )
    return overrides


def resolve_plan_media_payload(post: dict[str, Any]) -> dict[str, Any] | None:
    explicit = post.get("media")
    if isinstance(explicit, dict):
        return dict(explicit)

    payload: dict[str, Any] = {}
    mapping = {
        "mediaQuery": "query",
        "mediaProviders": "providers",
        "mediaUrls": "mediaUrls",
        "mediaCandidates": "candidates",
        "generatedMedia": "generatedMedia",
        "mediaOrientation": "orientation",
        "mediaLimit": "limit",
        "mediaMaxImages": "maxImages",
        "mediaStorageMode": "storageMode",
        "replaceExistingMedia": "replaceExisting",
        "altText": "altText",
    }
    for source_key, target_key in mapping.items():
        value = post.get(source_key)
        if value is not None:
            payload[target_key] = value
    return payload or None


def build_media_attach_body_from_args(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if args.query:
        body["query"] = args.query
    if args.providers:
        body["providers"] = args.providers
    if args.orientation:
        body["orientation"] = args.orientation
    if args.limit is not None:
        body["limit"] = args.limit
    if args.max_images is not None:
        body["maxImages"] = args.max_images
    if args.storage_mode:
        body["storageMode"] = args.storage_mode
    if args.alt_text:
        body["altText"] = args.alt_text
    if args.replace_existing:
        body["replaceExisting"] = True
    if args.media_urls:
        body["mediaUrls"] = args.media_urls
    if args.candidates_file:
        body["candidates"] = read_json_file(args.candidates_file)
    if args.generated_media_file:
        body["generatedMedia"] = read_json_file(args.generated_media_file)
    if not body:
        raise ApiError(
            "Provide attach-media input with --body-file/--body-json or one of --query, --media-url, --candidates-file, or --generated-media-file."
        )
    return body


def command_apply_plan(args: argparse.Namespace) -> None:
    plan = read_json_file(args.plan_file)
    campaign_payload = dict(plan.get("campaign") or {})
    if not campaign_payload:
        raise ApiError("Plan file must include a campaign object.")
    post_entries = list(plan.get("posts") or [])
    if not post_entries:
        raise ApiError("Plan file must include at least one post.")

    campaign = social_api_request(args, "POST", "campaigns", campaign_payload)
    created_posts: list[dict[str, Any]] = []

    for entry in post_entries:
        post = dict(entry)
        title = str(post.get("title", "")).strip()
        copy_text = str(post.get("copy", "")).strip()
        publish_at = str(post.get("publishAt", "")).strip()
        if not title or not copy_text or not publish_at:
            raise ApiError("Each post requires title, copy, and publishAt.")

        settings = build_plan_settings(post)
        create_payload = {
            "title": title,
            "rawIdea": copy_text,
            "campaignId": campaign["id"],
            "settings": settings,
        }
        created = social_api_request(args, "POST", "posts", create_payload)

        post_state = str(post.get("postState", "active"))
        patch_payload = {
            "title": title,
            "rawIdea": copy_text,
            "campaignId": campaign["id"],
            "postState": post_state,
            "metadata": {
                **dict(post.get("metadata") or {}),
                "postState": post_state,
                "settings": settings,
            },
            "variantOverrides": build_variant_overrides(post, settings),
        }
        updated = social_api_request(args, "PATCH", f"posts/{created['id']}", patch_payload)

        attach_result = None
        media_payload = resolve_plan_media_payload(post)
        if media_payload:
            attach_result = social_api_request(
                args, "POST", f"posts/{created['id']}/media", media_payload
            )

        schedule_payload = {
            "publishAt": publish_at,
            "postState": post_state,
            "settings": settings,
        }
        scheduled = social_api_request(
            args, "POST", f"posts/{created['id']}/schedule", schedule_payload
        )

        created_posts.append(
            {
                "id": updated["id"],
                "title": updated["title"],
                "publishAt": publish_at,
                "scheduleCount": len(list(scheduled.get("schedules") or [])),
                "rejected": list(scheduled.get("rejected") or []),
                "attachedAssetCount": (
                    len(list(attach_result.get("assets") or []))
                    if isinstance(attach_result, dict)
                    else 0
                ),
                "mediaWarnings": (
                    list(attach_result.get("warnings") or [])
                    if isinstance(attach_result, dict)
                    else []
                ),
            }
        )

    dump_json(
        {
            "campaign": campaign,
            "posts": created_posts,
        }
    )


def add_shared_api_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--org-id", default=DEFAULT_ORG_ID)
    parser.add_argument(
        "--auth-mode",
        choices=["none", "local-bypass", "bridge-token"],
        default="none",
    )
    parser.add_argument("--bridge-token", default=DEFAULT_BRIDGE_TOKEN)


def add_body_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--body-file")
    parser.add_argument("--body-json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Prompthon social campaigns and posts through the production social API."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    exchange = subparsers.add_parser("exchange-handoff")
    exchange.add_argument("--base-url", default=DEFAULT_BASE_URL)
    exchange.add_argument("--code", required=True)
    exchange.add_argument("--bridge-origin", default="http://127.0.0.1:4319")
    exchange.set_defaults(func=command_exchange_handoff)

    request_parser = subparsers.add_parser("request")
    add_shared_api_arguments(request_parser)
    request_parser.add_argument("--method", required=True)
    request_parser.add_argument("--path", required=True)
    add_body_arguments(request_parser)
    request_parser.set_defaults(func=command_request)

    list_channels = subparsers.add_parser("list-channels")
    add_shared_api_arguments(list_channels)
    list_channels.set_defaults(func=command_list_channels)

    list_campaigns = subparsers.add_parser("list-campaigns")
    add_shared_api_arguments(list_campaigns)
    list_campaigns.set_defaults(func=command_list_campaigns)

    list_posts = subparsers.add_parser("list-posts")
    add_shared_api_arguments(list_posts)
    list_posts.set_defaults(func=command_list_posts)

    get_post = subparsers.add_parser("get-post")
    add_shared_api_arguments(get_post)
    get_post.add_argument("--post-id", required=True)
    get_post.set_defaults(func=command_get_post)

    create_campaign = subparsers.add_parser("create-campaign")
    add_shared_api_arguments(create_campaign)
    add_body_arguments(create_campaign)
    create_campaign.set_defaults(func=command_create_campaign)

    update_campaign = subparsers.add_parser("update-campaign")
    add_shared_api_arguments(update_campaign)
    update_campaign.add_argument("--campaign-id", required=True)
    add_body_arguments(update_campaign)
    update_campaign.set_defaults(func=command_update_campaign)

    create_post = subparsers.add_parser("create-post")
    add_shared_api_arguments(create_post)
    add_body_arguments(create_post)
    create_post.set_defaults(func=command_create_post)

    update_post = subparsers.add_parser("update-post")
    add_shared_api_arguments(update_post)
    update_post.add_argument("--post-id", required=True)
    add_body_arguments(update_post)
    update_post.set_defaults(func=command_update_post)

    schedule_post = subparsers.add_parser("schedule-post")
    add_shared_api_arguments(schedule_post)
    schedule_post.add_argument("--post-id", required=True)
    schedule_post.add_argument("--publish-at")
    schedule_post.add_argument(
        "--post-state", choices=["draft", "active", "suspended"], default="active"
    )
    schedule_post.add_argument("--timezone", default="America/Toronto")
    add_body_arguments(schedule_post)
    schedule_post.set_defaults(func=command_schedule_post)

    search_media = subparsers.add_parser("search-media")
    add_shared_api_arguments(search_media)
    search_media.add_argument("--query")
    search_media.add_argument("--limit", type=int, default=12)
    search_media.add_argument("--per-provider", type=int, default=6)
    search_media.add_argument("--orientation")
    search_media.add_argument("--providers", nargs="*")
    add_body_arguments(search_media)
    search_media.set_defaults(func=command_search_media)

    attach_media = subparsers.add_parser("attach-media")
    add_shared_api_arguments(attach_media)
    attach_media.add_argument("--post-id", required=True)
    attach_media.add_argument("--query")
    attach_media.add_argument("--providers", nargs="*")
    attach_media.add_argument("--orientation")
    attach_media.add_argument("--limit", type=int)
    attach_media.add_argument("--max-images", type=int)
    attach_media.add_argument("--storage-mode")
    attach_media.add_argument("--alt-text")
    attach_media.add_argument("--replace-existing", action="store_true")
    attach_media.add_argument("--media-urls", nargs="*")
    attach_media.add_argument("--candidates-file")
    attach_media.add_argument("--generated-media-file")
    add_body_arguments(attach_media)
    attach_media.set_defaults(func=command_attach_media)

    rewrite_post = subparsers.add_parser("rewrite-post")
    add_shared_api_arguments(rewrite_post)
    rewrite_post.add_argument("--post-id", required=True)
    rewrite_post.add_argument("--tone", default="clear")
    rewrite_post.add_argument("--selection-file")
    rewrite_post.add_argument("--editor-context-file")
    add_body_arguments(rewrite_post)
    rewrite_post.set_defaults(func=command_rewrite_post)

    replace_selection = subparsers.add_parser("replace-selection")
    add_shared_api_arguments(replace_selection)
    replace_selection.add_argument("--post-id")
    replace_selection.add_argument("--editor-context-file", required=True)
    replace_selection.add_argument("--replacement-text")
    replace_selection.add_argument("--replacement-file")
    replace_selection.add_argument(
        "--post-state", choices=["draft", "active", "suspended"]
    )
    replace_selection.set_defaults(func=command_replace_selection)

    apply_plan = subparsers.add_parser("apply-plan")
    add_shared_api_arguments(apply_plan)
    apply_plan.add_argument("--plan-file", required=True)
    apply_plan.set_defaults(func=command_apply_plan)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except ApiError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
