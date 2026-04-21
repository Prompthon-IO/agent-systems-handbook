from dataclasses import dataclass, field


@dataclass
class MemoryItem:
    kind: str
    summary: str
    source: str


@dataclass
class AgentState:
    active_notes: list[str] = field(default_factory=list)
    working_memory: list[MemoryItem] = field(default_factory=list)
    retrieval_queries: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)


def add_observation(state: AgentState, note: str) -> None:
    state.active_notes.append(note)


def queue_retrieval(state: AgentState, query: str) -> None:
    state.retrieval_queries.append(query)


def promote_fact(state: AgentState, artifact_key: str, summary: str) -> None:
    state.artifacts[artifact_key] = summary


def remember(state: AgentState, kind: str, summary: str, source: str) -> None:
    state.working_memory.append(
        MemoryItem(kind=kind, summary=summary, source=source)
    )
