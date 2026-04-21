from typing import TypedDict


class GraphState(TypedDict):
    question: str
    plan: str
    route: str
    answer: str


def plan_node(state: GraphState) -> GraphState:
    state["plan"] = "break the question into one tool step and one synthesis step"
    return state


def route_node(state: GraphState) -> GraphState:
    state["route"] = "tool"
    return state


def synthesize_node(state: GraphState) -> GraphState:
    state["answer"] = "placeholder synthesis"
    return state
