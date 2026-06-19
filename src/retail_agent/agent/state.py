"""Typed state carried by the LangGraph retail-analysis workflow."""

from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from retail_agent.agent.enums import AgentOutcome


class GoldenTrioExample(TypedDict):
    """Serializable few-shot Trio injected into the SQL-generation prompt."""

    question: str
    sql: str
    report: str


class AgentState(TypedDict, total=False):
    """State shared by graph nodes and serialized by the checkpointer."""

    question: str
    masked_question: NotRequired[str | None]
    few_shot: NotRequired[list[GoldenTrioExample]]
    schema_context: NotRequired[str | None]
    sql: NotRequired[str | None]
    validation_error: NotRequired[str | None]
    masked_result_rows: NotRequired[list[dict[str, object]]]
    result_total_rows: NotRequired[int | None]
    result_truncated: NotRequired[bool]
    report: NotRequired[str | None]
    scrubbed_report: NotRequired[str | None]
    self_correct_count: NotRequired[int]
    last_error: NotRequired[str | None]
    outcome: NotRequired[AgentOutcome | None]
    trace_id: NotRequired[str]
    started_at: NotRequired[float]
    bq_bytes: NotRequired[int | None]
    run_trace: NotRequired[dict[str, object]]
    messages: Annotated[list[BaseMessage], add_messages]
