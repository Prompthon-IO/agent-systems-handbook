#!/usr/bin/env python3
"""Audit selected HTML/Markdown snapshots for answerability signals and recheck changes."""
from __future__ import annotations
import argparse
import hashlib
import re
import sys
import urllib.parse
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, file_hash, identifier, read_json, write_json

STOP = {"the", "a", "an", "is", "are", "for", "to", "of", "and", "how", "what", "who", "can", "do", "does", "i", "it"}


def words(text: str) -> set[str]:
    return set(re.findall(r"[\w]+", text.casefold())) - STOP


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.links, self.parts = [], [], []
        self.active, self.skip = None, 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        if self.skip:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "title"}:
            self.active = {"tag": tag, "line": self.getpos()[0], "pieces": []}
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.skip = max(0, self.skip - 1)
            return
        if not self.skip and self.active and tag == self.active["tag"]:
            block = self.active
            text = " ".join(" ".join(block.pop("pieces")).split())
            if text:
                self.blocks.append({**block, "text": text})
            self.active = None

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.active:
                self.active["pieces"].append(data)


def extract(path: Path) -> dict:
    payload = path.read_bytes()
    if len(payload) > 500_000:
        raise CourseError("PAGE_TOO_LARGE", "Use a selected readable page snapshot smaller than 500 KB.")
    text = payload.decode("utf-8-sig")
    if path.suffix.lower() in {".html", ".htm"}:
        page = PageText()
        page.feed(text)
        blocks, links, visible = page.blocks, page.links, " ".join(" ".join(page.parts).split())
    elif path.suffix.lower() == ".md":
        blocks, links, visible = [], [], []
        fenced = False
        for line, value in enumerate(text.splitlines(), 1):
            if value.strip().startswith("```"):
                fenced = not fenced
                continue
            if fenced or not value.strip():
                continue
            match = re.match(r"^(#{1,6})\s+(.+)", value)
            blocks.append({"tag": "h" + str(len(match[1])) if match else "p", "line": line, "text": match[2] if match else value.strip()})
            links.extend(re.findall(r"\]\((https?://[^\s)]+)\)", value))
            visible.append(value)
        visible = " ".join(visible)
    else:
        raise CourseError("UNSUPPORTED_FILE", "Select local UTF-8 HTML or Markdown snapshots, not executable/remote content.")
    return {"blocks": blocks, "links": links, "visible": visible, "sha256": hashlib.sha256(payload).hexdigest()}


def clean_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return ""
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def audit_site(root: Path, spec: dict) -> dict:
    if not isinstance(spec, dict) or not isinstance(spec.get("entity"), str) or not spec["entity"].strip():
        raise CourseError("INVALID_AUDIT", "Name the entity/product the pages should consistently explain.")
    queries, selected = spec.get("target_queries"), spec.get("pages")
    if not isinstance(queries, list) or not 1 <= len(queries) <= 20 or not all(isinstance(q, str) and words(q) for q in queries):
        raise CourseError("INVALID_AUDIT", "Supply 1–20 explicit audience questions.")
    if not isinstance(selected, list) or not 1 <= len(selected) <= 10:
        raise CourseError("INVALID_AUDIT", "Select 1–10 local page snapshots with path and source URL.")
    if not all(isinstance(entry, dict) and isinstance(entry.get("path"), str) and entry["path"].strip()
               and isinstance(entry.get("url"), str) and entry["url"].strip() for entry in selected):
        raise CourseError("INVALID_AUDIT", "Every page entry must be an object with nonempty path and source URL strings.")
    fields = spec.get("consistency_fields", [])
    if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
        raise CourseError("INVALID_AUDIT", "consistency_fields must be explicit fact labels such as duration or audience.")
    pages, findings, facts = [], [], defaultdict(list)
    def finding(code, page, evidence, recommendation, query=None):
        key = digest([code, page, query])[:24]
        findings.append({"id": key, "code": code, "source_ref": page, "query": query, "evidence": evidence, "recommended_change": recommendation})
    for entry in selected:
        rel = Path(entry["path"])
        path = root / rel
        if rel.is_absolute() or ".." in rel.parts or not path.is_file() or not path.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
            raise CourseError("UNSAFE_PATH", "Page snapshots must be nonsymlink files inside the selected site directory.")
        source_url = clean_url(entry.get("url", ""))
        if not source_url:
            raise CourseError("INVALID_AUDIT", "Each snapshot needs a noncredential source URL; use a clearly synthetic URL for fixtures.")
        page = extract(path)
        headings = [b for b in page["blocks"] if re.fullmatch(r"h[1-6]", b["tag"])]
        if sum(h["tag"] == "h1" for h in headings) != 1:
            finding("main_heading", rel.as_posix(), [{"h1_count": sum(h["tag"] == "h1" for h in headings)}], "Provide one descriptive main heading.")
        if spec["entity"].casefold() not in page["visible"][:500].casefold():
            finding("entity_positioning", rel.as_posix(), [{"excerpt": page["visible"][:180]}], "Name the entity/product and audience near the beginning, using consistent wording.")
        for previous, current in zip(headings, headings[1:]):
            if int(current["tag"][1]) > int(previous["tag"][1]) + 1:
                finding("heading_structure", rel.as_posix(), [{"line": current["line"], "heading": current["text"][:160]}], "Use a readable heading hierarchy without skipped levels.")
                break
        external_links = sorted({url for link in page["links"] if (url := clean_url(urllib.parse.urljoin(source_url, link))) and urllib.parse.urlsplit(url).netloc != urllib.parse.urlsplit(source_url).netloc})
        if not external_links:
            finding("evidence_attribution", rel.as_posix(), [], "Attribute factual claims to reviewable primary evidence; a link alone does not prove truth.")
        for block in page["blocks"]:
            match = re.match(r"^([\w -]{1,40}):\s*(.{1,120})$", block["text"])
            if match and match[1].strip().casefold() in {f.casefold() for f in fields}:
                facts[match[1].strip().casefold()].append({"source_ref": rel.as_posix(), "line": block["line"], "value": match[2].strip()})
        answers = []
        for query in queries:
            tokens = words(query)
            candidate = None
            for index, block in enumerate(page["blocks"]):
                if not block["tag"].startswith("h") or len(tokens & words(block["text"])) / len(tokens) < .6:
                    continue
                next_block = page["blocks"][index + 1] if index + 1 < len(page["blocks"]) else None
                if next_block and next_block["tag"] == "p" and 8 <= len(next_block["text"]) <= 500:
                    candidate = {"line": next_block["line"], "heading": block["text"][:180], "excerpt": next_block["text"][:200]}
                    break
            answers.append({"query": query, "signal": "candidate_direct_answer" if candidate else "no_structural_answer_found", "evidence": candidate, "accuracy": "requires_human_review"})
        if file_hash(path) != page["sha256"]:
            raise CourseError("SOURCE_CHANGED", "Page changed during extraction; rerun on a stable snapshot.")
        pages.append({"source_ref": rel.as_posix(), "source_url": source_url, "source_sha256": page["sha256"], "headings": [{"level": h["tag"], "text": h["text"][:180], "line": h["line"]} for h in headings], "evidence_links": external_links[:20], "answerability": answers})
    for query in queries:
        if not any(a["signal"] == "candidate_direct_answer" for p in pages for a in p["answerability"] if a["query"] == query):
            finding("answer_gap", "selected-site", [], "Add a concise, accurate answer under a descriptive question heading, supported by evidence.", query)
    for field, values in facts.items():
        if len({v["value"].casefold() for v in values}) > 1:
            finding("site_consistency", field, values, "Resolve differing stated values against the authoritative source; do not choose one automatically.")
    return {"entity": spec["entity"], "target_queries": queries, "scope_sha256": digest(spec), "pages": pages, "findings": findings,
            "limitations": ["Structural/text heuristics, not a search ranking or model-citation measurement", "No live fetch, indexing request, publication or guarantee of AI visibility", "Human review is required for factual correctness, evidence quality and natural-language equivalence"]}


def run_audit(store: Store, root: Path, spec: dict, audit_id: str, expected_revision: int) -> dict:
    identifier(audit_id, "audit id")
    previous = store.maybe_get("aeo_audits", audit_id)
    if (previous["revision"] if previous else 0) != expected_revision:
        raise CourseError("CONFLICT", "Read the previous audit revision before a recheck.")
    result = audit_site(root, spec)
    old = {f["id"] for f in previous["data"]["findings"]} if previous else set()
    current = {f["id"] for f in result["findings"]}
    comparable = not previous or previous["data"]["scope_sha256"] == result["scope_sha256"]
    result["recheck"] = {"previous_revision": expected_revision, "scope_comparable": comparable, "new": sorted(current - old), "still_open": sorted(current & old), "resolved": sorted(old - current) if comparable else [], "removed_by_scope_change": sorted(old - current) if not comparable else []}
    if store.config.dry_run:
        return {"status": "preview", **result}
    run = Run(store, "ai-search-visibility", "Inspect selected page snapshots for answerability and consistency")
    run.save("running")
    record = store.put("aeo_audits", audit_id, {"audit_id": audit_id, **result}, expected_revision=expected_revision)
    output = store.root / "aeo-audits" / audit_id / (str(record["revision"]) + ".json")
    write_json(output, record)
    run.artifact("aeo_audit", "Source-backed visibility signals", {"audit_id": audit_id, "revision": record["revision"], "findings": len(result["findings"]), "recheck": result["recheck"]})
    run.save("succeeded")
    return {"status": "succeeded", "run_id": run.id, "audit_id": audit_id, "revision": record["revision"], "report": str(output), **result}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    p.add_argument("--site", type=Path, required=True)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--audit-id", default="course-aeo")
    p.add_argument("--expected-revision", type=int, default=0)
    a = p.parse_args()
    emit(run_audit(Store(Config.from_args(a)), a.site, read_json(a.spec), a.audit_id, a.expected_revision))


if __name__ == "__main__":
    cli_main(main)
