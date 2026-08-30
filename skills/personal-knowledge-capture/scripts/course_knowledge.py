#!/usr/bin/env python3
"""Incremental multi-source capture using the existing extractors; originals are read-only."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, file_hash, identifier, read_json, write_json
import personal_knowledge_capture as baseline


def collect(folder: Path, store: Store, *, dry_run: bool = False) -> tuple[list, list]:
    if not folder.is_dir() or folder.is_symlink():
        raise CourseError("INVALID_INPUT", "Name a source directory containing course material.")
    folder = folder.resolve()
    sources, skipped = [], []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".markdown", ".txt", ".pdf", ".docx"}:
            continue
        relative = path.relative_to(folder).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(folder) or path.stat().st_size > 5_000_000:
            skipped.append({"source_ref": relative, "reason": "symlink_or_oversized"})
            continue
        source_id = "src-" + digest([str(folder), relative])[:24]
        hashed, modified = file_hash(path), path.stat().st_mtime_ns
        cache = store.root / "knowledge-cache" / (source_id + ".json")
        previous = read_json(cache) if cache.exists() else None
        try:
            if previous and previous["sha256"] == hashed and previous["modified_ns"] == modified:
                title, text, change = previous["title"], previous["text"], "unchanged"
            else:
                title, text = baseline.extract_local_text(path)
                change = "modified" if previous else "new"
            text = text[:40_000]
            if not dry_run:
                write_json(cache, {"sha256": hashed, "modified_ns": modified, "title": title, "text": text})
            sources.append({"id": source_id, "source_type": "local_file", "source_ref": relative,
                            "title": title, "sha256": hashed, "modified_ns": modified, "change": change,
                            "text_hash": digest(" ".join(text.split()).lower()), "text": text})
        except Exception as exc:
            skipped.append({"source_ref": relative, "reason": type(exc).__name__})
    return sources, skipped


def synthesize(sources: list, skipped: list) -> dict:
    unique, by_hash, claims = [], {}, {}
    for source in sources:
        if source["text_hash"] in by_hash:
            source["duplicate_of"] = by_hash[source["text_hash"]]["id"]
        else:
            by_hash[source["text_hash"]] = source
            unique.append(source)
        for line_no, line in enumerate(source["text"].splitlines(), 1):
            match = re.fullmatch(r"\s*([\w][\w -]{1,50}):\s*(.{1,180})\s*", line)
            if match:
                key, value = match.group(1).strip().lower(), match.group(2).strip()
                claims.setdefault(key, {}).setdefault(value, []).append({"source_id": source["id"], "line": line_no})
    conflicts = [{"field": key, "alternatives": [{"value": value, "citations": refs} for value, refs in alternatives.items()]} for key, alternatives in claims.items() if len(alternatives) > 1]
    insights = [{"text": baseline.concise_summary(s["text"]), "source_id": s["id"]} for s in unique]
    actions = [{"text": m.group(1), "source_id": s["id"]} for s in unique for m in re.finditer(r"(?im)^action:\s*(.+)$", s["text"])]
    return {"summary": "Source-grounded extractive draft; review with Codex before treating it as a synthesis.",
            "key_insights": insights, "action_notes": actions, "conflicts": conflicts,
            "source_refs": [{k: v for k, v in s.items() if k != "text"} for s in sources],
            "skipped": skipped, "unique_sources": len(unique), "duplicates": len(sources) - len(unique),
            "limitations": ["Conflicts detect explicit field:value differences only; ask Codex to review semantic contradictions.",
                            "Modification time is freshness evidence, not proof of authority. Source authority is unassessed."]}


def markdown(note: dict) -> str:
    lines = ["# Summary", "", note["summary"], "", "## New Files", ""]
    lines += [f"- {s['source_ref']} ({s['change']})" for s in note["source_refs"]]
    lines += ["", "## Key Insights", ""] + [f"- {x['text']} [{x['source_id']}]" for x in note["key_insights"]]
    lines += ["", "## Actionable Notes", ""] + [f"- {x['text']} [{x['source_id']}]" for x in note["action_notes"]]
    lines += ["", "## Open Questions", "", "Review source authority and resolve these conflicting statements:"]
    lines += [f"- {c['field']}: " + "; ".join(f"{v['value']} [{','.join(r['source_id'] for r in v['citations'])}]" for v in c["alternatives"]) for c in note["conflicts"]]
    lines += ["", "## Source References", ""] + [f"- [{s['id']}] {s['source_ref']}; SHA-256 {s['sha256']}; modified_ns {s['modified_ns']}" for s in note["source_refs"]]
    lines += ["", "## Limitations", ""] + ["- " + x for x in note["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("synthesize")
    s.add_argument("--folder", type=Path, required=True)
    s.add_argument("--note-id", default="weekly-note")
    s.add_argument("--share-content", action="store_true", help="Explicitly permit extracted text upload in addition to the derived note.")
    show = sub.add_parser("show")
    show.add_argument("--note-id", default="weekly-note")
    a = p.parse_args()
    store = Store(Config.from_args(a))
    identifier(a.note_id, "note id")
    if a.command == "show":
        emit(store.get("knowledge_notes", a.note_id))
        return
    store.context("course:write")
    sources, skipped = collect(a.folder.resolve(), store, dry_run=a.dry_run)
    note = synthesize(sources, skipped)
    if not sources:
        raise CourseError("NO_SOURCES", "No supported sources could be extracted; inspect the folder or optional PDF dependency.")
    if a.share_content:
        note["approved_extracted_text"] = [{"source_id": s["id"], "text": s["text"]} for s in sources if not s.get("duplicate_of")]
    if a.dry_run:
        emit({"status": "preview", "note": note})
        return
    run = Run(store, "personal-knowledge-capture", "Synthesize explicitly selected course sources")
    run.save("running")
    for source in note["source_refs"]:
        prior = store.maybe_get("knowledge_sources", source["id"])
        store.put("knowledge_sources", source["id"], source, expected_revision=prior["revision"] if prior else 0)
    previous = store.maybe_get("knowledge_notes", a.note_id)
    record = store.put("knowledge_notes", a.note_id, note, expected_revision=previous["revision"] if previous else 0)
    output = store.root / "knowledge-notes" / (a.note_id + ".md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown(note), encoding="utf-8")
    run.data["source_refs"] = note["source_refs"]
    run.artifact("knowledge_note", "Verified knowledge note", {"note_id": a.note_id, "revision": record["revision"], "unique_sources": note["unique_sources"], "duplicates": note["duplicates"], "conflicts": len(note["conflicts"])})
    run.save("partial" if skipped else "succeeded")
    emit({"status": "partial" if skipped else "succeeded", "run_id": run.id, "note_id": a.note_id, "revision": record["revision"], "note_path": str(output), "unique_sources": note["unique_sources"], "duplicates": note["duplicates"], "conflicts": note["conflicts"], "skipped": skipped})


if __name__ == "__main__":
    cli_main(main)
