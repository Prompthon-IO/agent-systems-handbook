from dataclasses import dataclass


@dataclass
class PersonalContextFact:
    category: str
    summary: str
    source: str


def normalize_imported_context(
    pairs: list[tuple[str, str]],
    source: str = "imported-summary",
) -> list[PersonalContextFact]:
    facts: list[PersonalContextFact] = []
    for category, summary in pairs:
        cleaned_category = category.strip().lower().replace(" ", "_")
        cleaned_summary = summary.strip()
        if not cleaned_category or not cleaned_summary:
            continue
        facts.append(
            PersonalContextFact(
                category=cleaned_category,
                summary=cleaned_summary,
                source=source,
            )
        )
    return facts


def merge_personal_context(
    existing: list[PersonalContextFact],
    imported: list[PersonalContextFact],
) -> list[PersonalContextFact]:
    merged = {fact.category: fact for fact in existing}
    for fact in imported:
        merged[fact.category] = fact
    return list(merged.values())
