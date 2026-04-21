from dataclasses import dataclass, field


@dataclass
class Evidence:
    title: str
    url: str
    summary: str


@dataclass
class ResearchTask:
    question: str
    todo: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


def seed_plan(task: ResearchTask) -> None:
    task.todo.extend(
        [
            "clarify the research goal",
            "collect evidence",
            "synthesize a cited answer",
        ]
    )


def add_evidence(task: ResearchTask, title: str, url: str, summary: str) -> None:
    task.evidence.append(Evidence(title=title, url=url, summary=summary))


def draft_report(task: ResearchTask) -> str:
    lines = [f"# Research Draft\n\nQuestion: {task.question}\n"]
    for item in task.evidence:
        lines.append(f"- {item.title} ({item.url}): {item.summary}")
    return "\n".join(lines)
