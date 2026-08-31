#!/usr/bin/env python3
"""Preview a normalization plan, then write a new clean dataset without changing its source."""
import argparse
import csv
import io
import sys
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, file_hash, identifier, read_json, require_approval, write_json
from course_table import normalize, read_table, safe_csv_value


def preview(source: Path, schema: dict, sheet: str | None = None, dedupe: bool = False) -> dict:
    headers, rows, evidence = read_table(source, sheet)
    result = normalize(headers, rows, schema, dedupe)
    plan = {"source": evidence, **result}
    return {"status": "preview", "plan_sha256": digest(plan), **plan}


def apply(store: Store, source: Path, output: Path, dataset_id: str, schema: dict, confirm: str | None, sheet: str | None = None, dedupe: bool = False, share_rows: bool = False) -> dict:
    identifier(dataset_id, "dataset id")
    plan = preview(source, schema, sheet, dedupe)
    if output.exists() or output.is_symlink() or source.resolve() == output.resolve():
        raise CourseError("OUTPUT_EXISTS", "Choose a new output directory; source and existing outputs are never overwritten.")
    if store.config.dry_run:
        return plan
    require_approval(confirm, plan["plan_sha256"])
    if plan["errors"]:
        raise CourseError("REVIEW_REQUIRED", "Some values do not match the reviewed schema. Correct the source copy or schema; do not silently discard rows.")
    run = Run(store, "business-data-structuring", "Normalize a reviewed synthetic business dataset")
    run.save("running")
    data = {k: v for k, v in plan.items() if k not in {"rows", "status"}}
    data["dataset_id"] = dataset_id
    data["rows_stored"] = store.config.storage == "local" or share_rows
    if data["rows_stored"]:
        data["rows"] = plan["rows"]
    # Keep the output and its digest durable before remote registration for failure recovery.
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "clean.json", {"source": plan["source"], "columns": plan["columns"], "grain": plan["grain"], "rows": plan["rows"]})
    with (output / "clean.csv").open("x", encoding="utf-8", newline="") as stream:
        fields = [c["name"] for c in plan["columns"]]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in plan["rows"]:
            writer.writerow({k: safe_csv_value(v) for k, v in row.items()})
    write_json(output / "review.json", {k: v for k, v in plan.items() if k != "rows"})
    data["artifacts"] = [{"source_ref": name, "sha256": file_hash(output / name)} for name in ("clean.json", "clean.csv", "review.json")]
    previous = store.maybe_get("business_datasets", dataset_id)
    rec = store.put("business_datasets", dataset_id, data, expected_revision=previous["revision"] if previous else 0)
    run.artifact("business_dataset", "Clean dataset and normalization evidence", {"dataset_id": dataset_id, "revision": rec["revision"], "artifacts": data["artifacts"]})
    run.save("succeeded")
    return {"status": "succeeded", "run_id": run.id, "dataset_id": dataset_id, "revision": rec["revision"], "output": str(output), "shape": plan["shape"], "rows_stored": data["rows_stored"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("preview", "apply"):
        s = sub.add_parser(name)
        s.add_argument("--source", type=Path, required=True)
        s.add_argument("--schema", type=Path, required=True)
        s.add_argument("--sheet")
        s.add_argument("--dedupe", action="store_true", help="Remove exact normalized duplicates only after the plan is reviewed.")
        if name == "apply":
            s.add_argument("--output", type=Path, required=True)
            s.add_argument("--dataset-id", default="course-pipeline")
            s.add_argument("--confirm")
            s.add_argument("--share-rows", action="store_true", help="Explicitly permit cleaned synthetic rows in the remote course record.")
    a = p.parse_args()
    schema = read_json(a.schema)
    result = preview(a.source, schema, a.sheet, a.dedupe) if a.command == "preview" else apply(Store(Config.from_args(a)), a.source, a.output, a.dataset_id, schema, a.confirm, a.sheet, a.dedupe, a.share_rows)
    emit(result)


if __name__ == "__main__":
    cli_main(main)
