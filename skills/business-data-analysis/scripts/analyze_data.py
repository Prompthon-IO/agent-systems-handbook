#!/usr/bin/env python3
"""Read-only source profiling and reproducible business metrics with explicit evidence."""
from __future__ import annotations
import argparse
import json
import statistics
import sys
import uuid
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        sys.path.insert(0, str(parent / "skills/business-data-structuring/scripts"))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, file_hash, read_json, write_json
from course_table import normalize, read_table


def load_source(store: Store, source: Path | None, dataset_id: str | None, schema: dict, sheet: str | None) -> tuple[dict, dict]:
    if dataset_id:
        record = store.get("business_datasets", dataset_id)
        if not record["data"].get("rows_stored") or "rows" not in record["data"]:
            raise CourseError("LOCAL_ARTIFACT_REQUIRED", "This record contains metadata only. Analyze the explicitly selected local clean.json; do not invent missing rows.")
        return record["data"], {"dataset_id": dataset_id, "revision": record["revision"], "source": record["data"]["source"]}
    if source.suffix.lower() == ".json":
        data = read_json(source)
        if not isinstance(data, dict) or not isinstance(data.get("columns"), list) or not isinstance(data.get("rows"), list):
            raise CourseError("INVALID_DATASET", "JSON analysis input must be Structure's clean.json, with columns and rows.")
        return data, {"source_ref": source.name, "source_sha256": file_hash(source), "original_source": data.get("source")}
    headers, rows, evidence = read_table(source, sheet)
    return normalize(headers, rows, schema), evidence


def analyze(data: dict, source: dict) -> dict:
    rows, columns = data["rows"], data["columns"]
    if not rows or len(rows) > 10000 or not columns:
        raise CourseError("INVALID_DATASET", "Analysis needs 1–10,000 rows and explicit columns.")
    names = [c["name"] for c in columns]
    if any(not isinstance(row, dict) or set(row) != set(names) for row in rows):
        raise CourseError("INVALID_DATASET", "Every row must match the declared columns.")
    nulls = {name: sum(row[name] is None or str(row[name]).strip() == "" for row in rows) for name in names}
    duplicate_count = len(rows) - len({digest(row) for row in rows})
    numeric, categorical, suspicious = {}, {}, []
    for column in columns:
        name, kind = column["name"], column["type"]
        values = [(index, row[name]) for index, row in enumerate(rows, 2) if row[name] not in (None, "")]
        if kind in {"number", "currency"}:
            groups = defaultdict(list)
            for index, raw in values:
                try:
                    value = Decimal(str(raw))
                    if not value.is_finite():
                        raise ValueError()
                except (ValueError, InvalidOperation):
                    suspicious.append({"row": index, "column": name, "reason": "invalid_numeric"})
                    continue
                currency = str(rows[index - 2].get("currency") or column.get("currency") or "unspecified") if kind == "currency" or name in {"value", "deal_value", "amount", "revenue"} else "unitless"
                groups[currency].append((index, value))
                if value < 0:
                    suspicious.append({"row": index, "column": name, "reason": "negative_value_review"})
            numeric[name] = {}
            for unit, pairs in groups.items():
                nums = [v for _, v in pairs]
                summary = {"count": len(nums), "min": str(min(nums)), "max": str(max(nums)), "sum": str(sum(nums)), "mean": str(sum(nums) / len(nums)), "median": str(statistics.median(nums))}
                numeric[name][unit] = summary
                if len(nums) >= 4:
                    q1, _, q3 = statistics.quantiles(nums, n=4, method="inclusive")
                    iqr = q3 - q1
                    for row_index, value in pairs:
                        if iqr and (value < q1 - Decimal("1.5") * iqr or value > q3 + Decimal("1.5") * iqr):
                            suspicious.append({"row": row_index, "column": name, "reason": "outside_1.5_iqr", "unit": unit})
        elif kind == "text":
            counts = Counter(str(value) for _, value in values)
            # Do not persist row-level contact identifiers disguised as a categorical report.
            if name not in {"name", "contact_name", "email", "phone", "address"} and len(counts) <= 20:
                categorical[name] = dict(sorted(counts.items()))
            else:
                categorical[name] = {"distinct_count": len(counts), "values_omitted": True}
    metrics = {}
    if "stage" in names:
        stages = Counter(str(row.get("stage") or "missing").casefold() for row in rows)
        closed = stages["won"] + stages["lost"]
        metrics = {"deal_counts_by_stage": dict(stages), "closed_deals": closed,
                   "win_rate_closed_only": str(Decimal(stages["won"]) / closed) if closed else None,
                   "win_rate_denominator": "won + lost rows; assumes one deal per row"}
        amount = next((c for c in columns if c["name"] in {"deal_value", "value", "amount"} and c["type"] in {"number", "currency"}), None)
        if amount:
            open_values, won_values = defaultdict(Decimal), defaultdict(Decimal)
            invalid = 0
            for row in rows:
                raw = row[amount["name"]]
                try:
                    value = Decimal(str(raw))
                    if not value.is_finite():
                        raise ValueError()
                except (ValueError, InvalidOperation):
                    invalid += 1
                    continue
                currency = str(row.get("currency") or amount.get("currency") or "unspecified")
                stage = str(row.get("stage") or "").casefold()
                if stage == "won":
                    won_values[currency] += value
                elif stage in {"lead", "qualified", "proposal"}:
                    open_values[currency] += value
            metrics.update(open_pipeline_by_currency={k: str(v) for k, v in open_values.items()}, won_value_by_currency={k: str(v) for k, v in won_values.items()}, excluded_invalid_amount_rows=invalid)
    questions = ["Does one row represent one deal, one contact, or repeated activity?", "Which source resolves missing or suspicious values?"]
    if duplicate_count:
        questions.append("Are exact duplicate rows repeated events or accidental copies? Resolve before summing.")
    if any(nulls.values()):
        questions.append("Are nulls unknown, not applicable, or missing because of an import problem?")
    questions.append("What date range and denominator make the reported business metric meaningful?")
    return {"overview": {"rows": len(rows), "columns": len(columns), "grain": data.get("grain", "unspecified"), "column_types": {c["name"]: c["type"] for c in columns}},
            "data_quality": {"null_counts": nulls, "exact_duplicate_rows": duplicate_count, "normalization_errors": data.get("errors", []), "suspicious_values": suspicious},
            "key_patterns": {"categorical_distributions": categorical, "numeric_summary_by_unit": numeric},
            "business_insights": {"metrics": metrics, "interpretation": "Descriptive sample metrics only. Confirm grain and duplicates before using totals; no causal claim or forecast."},
            "recommended_next_questions": questions, "source_query_evidence": {**source, "row_digest": digest(rows), "calculation": "All selected rows; no implicit filtering, no currency conversion, no SQL mutation"}}


def run_analysis(store: Store, source: Path | None, dataset_id: str | None, schema: dict, sheet: str | None = None) -> dict:
    data, evidence = load_source(store, source, dataset_id, schema, sheet)
    report = analyze(data, evidence)
    if store.config.dry_run:
        return {"status": "preview", **report}
    run = Run(store, "business-data-analysis", "Read-only dataset profile and business evidence")
    run.save("running")
    analysis_id = str(uuid.uuid4())
    report_dir = store.root / "analysis" / analysis_id
    write_json(report_dir / "report.json", report)
    labels = [("Overview", "overview"), ("Data Quality", "data_quality"), ("Key Patterns", "key_patterns"), ("Business Insights", "business_insights"), ("Recommended Next Questions", "recommended_next_questions"), ("Source / Query Evidence", "source_query_evidence")]
    markdown = "# Business dataset analysis\n\n" + "\n\n".join("## " + title + "\n\n```json\n" + json.dumps(report[key], ensure_ascii=False, indent=2) + "\n```" for title, key in labels) + "\n"
    (report_dir / "report.md").write_text(markdown, encoding="utf-8")
    store.put("analysis_runs", analysis_id, {"analysis_id": analysis_id, **report, "report_ref": "report.md", "report_sha256": file_hash(report_dir / "report.md")})
    run.artifact("business_analysis", "Read-only report", {"analysis_id": analysis_id, "source_digest": report["source_query_evidence"]["row_digest"]})
    run.save("succeeded")
    return {"status": "succeeded", "run_id": run.id, "analysis_id": analysis_id, "report": str(report_dir / "report.md"), **report}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    selected = p.add_mutually_exclusive_group(required=True)
    selected.add_argument("--source", type=Path)
    selected.add_argument("--dataset-id")
    p.add_argument("--schema", type=Path)
    p.add_argument("--sheet")
    a = p.parse_args()
    emit(run_analysis(Store(Config.from_args(a)), a.source, a.dataset_id, read_json(a.schema) if a.schema else {}, a.sheet))


if __name__ == "__main__":
    cli_main(main)
