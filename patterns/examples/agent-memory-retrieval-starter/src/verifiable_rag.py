from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StoredFile:
    file_id: str
    title: str
    modality: str
    metadata: dict[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    file_id: str
    snippet: str
    score: float
    page_number: int | None = None
    media_id: str | None = None
    metadata: dict[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True)
class Citation:
    file_id: str
    title: str
    snippet: str
    page_number: int | None = None
    media_id: str | None = None
    metadata: dict[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True)
class GroundedAnswerPlan:
    query: str
    applied_filters: dict[str, str | int]
    selected_file_ids: list[str]
    citations: list[Citation]


def filter_files(
    files: list[StoredFile],
    required_filters: dict[str, str | int],
) -> list[StoredFile]:
    if not required_filters:
        return list(files)

    selected: list[StoredFile] = []
    for stored_file in files:
        if all(stored_file.metadata.get(key) == value for key, value in required_filters.items()):
            selected.append(stored_file)
    return selected


def build_grounded_plan(
    query: str,
    files: list[StoredFile],
    chunks: list[RetrievedChunk],
    required_filters: dict[str, str | int],
    *,
    min_score: float = 0.75,
    limit: int = 3,
) -> GroundedAnswerPlan:
    allowed_files = {
        stored_file.file_id: stored_file
        for stored_file in filter_files(files, required_filters)
    }
    ranked_chunks = sorted(chunks, key=lambda chunk: chunk.score, reverse=True)

    selected_file_ids: list[str] = []
    citations: list[Citation] = []

    for chunk in ranked_chunks:
        if chunk.score < min_score:
            continue
        stored_file = allowed_files.get(chunk.file_id)
        if stored_file is None:
            continue
        if chunk.file_id not in selected_file_ids:
            selected_file_ids.append(chunk.file_id)
        citations.append(
            Citation(
                file_id=chunk.file_id,
                title=stored_file.title,
                snippet=chunk.snippet,
                page_number=chunk.page_number,
                media_id=chunk.media_id,
                metadata={**stored_file.metadata, **chunk.metadata},
            )
        )
        if len(citations) >= limit:
            break

    return GroundedAnswerPlan(
        query=query,
        applied_filters=dict(required_filters),
        selected_file_ids=selected_file_ids,
        citations=citations,
    )


def render_citation_lines(plan: GroundedAnswerPlan) -> list[str]:
    lines: list[str] = []
    for citation in plan.citations:
        location_parts: list[str] = []
        if citation.page_number is not None:
            location_parts.append(f"p{citation.page_number}")
        if citation.media_id:
            location_parts.append(f"media:{citation.media_id}")
        location_text = f" ({', '.join(location_parts)})" if location_parts else ""
        lines.append(f"{citation.title}{location_text}")
    return lines
