"""Synchronous LangGraph workflow for the retail-analysis agent."""

import logging
import re
import time
from collections.abc import Callable
from typing import Any, cast

import openai
import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict

from retail_agent.agent.enums import AgentOutcome, NodeRoute
from retail_agent.agent.prompts import build_sql_messages
from retail_agent.agent.state import AgentState
from retail_agent.const import MAX_SELF_CORRECT_ITERATIONS
from retail_agent.exceptions import (
    BigQueryExecutionError,
    CostBudgetExceededError,
    DisallowedTableError,
    EmbeddingError,
    GoldenBucketError,
    MultiStatementError,
    SqlValidationError,
)
from retail_agent.repositories.postgres import build_postgres_saver, close_checkpointer_pool
from retail_agent.services.llm import build_chat_model
from retail_agent.services.observability import TraceCollector
from retail_agent.services.query_execution import QueryExecutionService
from retail_agent.services.reporting import generate_report
from retail_agent.services.retrieval import GoldenRetrievalService
from retail_agent.services.safety import (
    GuardDecision,
    classify_and_guard,
    is_schema_question,
    mask_question,
    scrub_report,
)
from retail_agent.services.schema import SchemaService
from retail_agent.services.sql_validation import validate_read_only_sql
from retail_agent.services.text_utils import content_to_text

logger = logging.getLogger(__name__)
SQL_FENCE_RE = re.compile(r"^\s*```(?:sql)?\s*(.*?)\s*```\s*$", re.IGNORECASE | re.DOTALL)
COLLECTORS: dict[str, TraceCollector] = {}
FAILED_RESPONSE = (
    "I could not produce a reliable answer for that question. Please narrow the request or try a simpler aggregation."
)
NO_DATA_RESPONSE = "No matching data was returned for this question."
COST_RESPONSE = "The query is too large to run within the configured cost limit."


class AgentDependencies(BaseModel):
    """Injectable graph dependencies used by tests, CLI and eval runs."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    chat_model_builder: Callable[[], BaseChatModel] = build_chat_model
    guard_classifier: Callable[..., GuardDecision] = classify_and_guard
    retrieval_service: GoldenRetrievalService = GoldenRetrievalService()
    schema_service: SchemaService = SchemaService()
    sql_validator: Callable[[str], object] = validate_read_only_sql
    query_execution_service: QueryExecutionService = QueryExecutionService()
    report_generator: Callable[..., str] = generate_report
    report_scrubber: Callable[[str], str] = scrub_report
    trace_factory: Callable[[str | None], TraceCollector] = TraceCollector


def _default_state(state: AgentState) -> AgentState:
    return {
        "question": state["question"],
        "masked_question": None,
        "few_shot": [],
        "schema_context": None,
        "sql": None,
        "validation_error": None,
        "masked_result_rows": [],
        "report": None,
        "scrubbed_report": None,
        "self_correct_count": 0,
        "last_error": None,
        "outcome": None,
        "bq_bytes": None,
        "run_trace": {},
    }


def _new_trace(dependencies: AgentDependencies, trace_id: str | None) -> TraceCollector:
    collector = dependencies.trace_factory(trace_id)
    COLLECTORS[collector.trace_id] = collector
    return collector


def _collector_for(state: AgentState, dependencies: AgentDependencies) -> TraceCollector:
    trace_id = state.get("trace_id")
    if trace_id and trace_id in COLLECTORS:
        return COLLECTORS[trace_id]
    return _new_trace(dependencies, trace_id)


def _callback_config(collector: TraceCollector) -> RunnableConfig:
    return {"callbacks": [collector]}


def _extract_sql(text: str) -> str:
    match = SQL_FENCE_RE.match(text)
    return match.group(1).strip() if match else text.strip().rstrip(";")


def _frame_to_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], df.astype(object).where(pd.notna(df), None).to_dict(orient="records"))


def _rows_to_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame.from_records(rows)


def _should_retry(state: AgentState) -> bool:
    return state.get("self_correct_count", 0) < MAX_SELF_CORRECT_ITERATIONS


def _finalize_state(state: AgentState, dependencies: AgentDependencies, outcome: AgentOutcome) -> AgentState:
    collector = _collector_for(state, dependencies)
    started_at = state.get("started_at", time.perf_counter())
    trace = collector.finalize(
        outcome=outcome,
        total_latency_sec=time.perf_counter() - started_at,
        bigquery_bytes=state.get("bq_bytes"),
        self_correct_iterations=state.get("self_correct_count", 0),
        error=state.get("last_error"),
    )
    COLLECTORS.pop(collector.trace_id, None)
    text = state.get("scrubbed_report") or state.get("report") or ""
    return {"outcome": outcome, "run_trace": trace.model_dump(mode="json"), "messages": [AIMessage(content=text)]}


def _build_nodes(dependencies: AgentDependencies) -> dict[str, Callable[[AgentState], AgentState]]:
    def guard(state: AgentState) -> AgentState:
        collector = _new_trace(dependencies, None)
        question = state["question"]
        masked_question = mask_question(question)
        model = dependencies.chat_model_builder()
        update = _default_state(state)
        update.update(
            {
                "masked_question": masked_question,
                "trace_id": collector.trace_id,
                "started_at": time.perf_counter(),
                "messages": [HumanMessage(content=question)],
            }
        )
        try:
            decision = dependencies.guard_classifier(masked_question, model, config=_callback_config(collector))
        except (openai.OpenAIError, RuntimeError, TimeoutError, ValueError) as exc:
            update.update({"outcome": AgentOutcome.FAILED, "last_error": str(exc), "report": FAILED_RESPONSE})
            return update
        if not decision.allowed:
            refusal = decision.refusal or FAILED_RESPONSE
            update.update(
                {
                    "outcome": AgentOutcome.BLOCKED,
                    "last_error": decision.reason,
                    "report": refusal,
                    "scrubbed_report": refusal,
                }
            )
        return update

    def refuse(state: AgentState) -> AgentState:
        return {"scrubbed_report": state.get("scrubbed_report") or FAILED_RESPONSE}

    def retrieve_golden(state: AgentState) -> AgentState:
        masked = mask_question(state["question"])
        try:
            retrieval = dependencies.retrieval_service.retrieve(state["question"])
        except (EmbeddingError, GoldenBucketError, openai.OpenAIError, RuntimeError, TimeoutError) as exc:
            logger.warning(
                "golden retrieval unavailable",
                extra={"trace_id": state.get("trace_id"), "error": str(exc)},
            )
            return {"masked_question": masked, "few_shot": [], "last_error": str(exc)}
        return {"masked_question": retrieval.masked_question, "few_shot": retrieval.examples}

    def generate_sql(state: AgentState) -> AgentState:
        collector = _collector_for(state, dependencies)
        try:
            schema_context = state.get("schema_context") or dependencies.schema_service.load_context()
        except BigQueryExecutionError as exc:
            return {"outcome": AgentOutcome.FAILED, "last_error": str(exc), "report": FAILED_RESPONSE}
        model = dependencies.chat_model_builder()
        masked_question = state.get("masked_question") or mask_question(state["question"])
        messages = build_sql_messages(
            question=masked_question,
            schema_context=schema_context,
            few_shot=state.get("few_shot", []),
            previous_sql=state.get("sql"),
            error=state.get("validation_error") or state.get("last_error"),
        )
        try:
            response = model.invoke(messages, config=_callback_config(collector))
        except (openai.OpenAIError, RuntimeError, TimeoutError, ValueError) as exc:
            return {"outcome": AgentOutcome.FAILED, "last_error": str(exc), "report": FAILED_RESPONSE}
        return {
            "schema_context": schema_context,
            "sql": _extract_sql(content_to_text(response.content)),
            "validation_error": None,
            "last_error": None,
        }

    def schema_report(state: AgentState) -> AgentState:
        try:
            schema_context = state.get("schema_context") or dependencies.schema_service.load_context()
        except BigQueryExecutionError as exc:
            return {"outcome": AgentOutcome.FAILED, "last_error": str(exc), "report": FAILED_RESPONSE}
        report_text = "Available dataset tables and columns:\n" + schema_context
        return {
            "outcome": AgentOutcome.OK,
            "schema_context": schema_context,
            "report": report_text,
            "scrubbed_report": report_text,
        }

    def validate_sql(state: AgentState) -> AgentState:
        sql = state.get("sql")
        if not sql:
            return {"validation_error": "SQL generation returned an empty statement", "last_error": "empty SQL"}
        try:
            dependencies.sql_validator(sql)
        except (SqlValidationError, MultiStatementError, DisallowedTableError) as exc:
            return {"validation_error": str(exc), "last_error": str(exc)}
        return {"validation_error": None, "last_error": None}

    def self_correct(state: AgentState) -> AgentState:
        return {"self_correct_count": state.get("self_correct_count", 0) + 1}

    def run_sql(state: AgentState) -> AgentState:
        sql = state.get("sql")
        if not sql:
            return {"last_error": "empty SQL"}
        try:
            execution = dependencies.query_execution_service.execute(sql)
        except CostBudgetExceededError as exc:
            return {"outcome": AgentOutcome.COST_EXCEEDED, "last_error": str(exc), "bq_bytes": exc.estimated_bytes}
        except BigQueryExecutionError as exc:
            return {"last_error": str(exc)}
        return {
            "masked_result_rows": _frame_to_rows(execution.masked_frame),
            "bq_bytes": execution.estimated_bytes,
            "last_error": None,
        }

    def no_data_report(_state: AgentState) -> AgentState:
        return {"outcome": AgentOutcome.NO_DATA, "report": NO_DATA_RESPONSE, "scrubbed_report": NO_DATA_RESPONSE}

    def cost_refusal(_state: AgentState) -> AgentState:
        return {"report": COST_RESPONSE, "scrubbed_report": COST_RESPONSE}

    def failure_response(_state: AgentState) -> AgentState:
        return {"outcome": AgentOutcome.FAILED, "report": FAILED_RESPONSE, "scrubbed_report": FAILED_RESPONSE}

    def report(state: AgentState) -> AgentState:
        collector = _collector_for(state, dependencies)
        model = dependencies.chat_model_builder()
        masked_df = _rows_to_frame(state.get("masked_result_rows", []))
        masked_question = state.get("masked_question") or mask_question(state["question"])
        try:
            text = dependencies.report_generator(
                masked_question,
                masked_df,
                model,
                config=_callback_config(collector),
            )
        except (openai.OpenAIError, RuntimeError, TimeoutError, ValueError) as exc:
            return {"outcome": AgentOutcome.FAILED, "last_error": str(exc), "report": FAILED_RESPONSE}
        return {"report": text}

    def scrub(state: AgentState) -> AgentState:
        return {"outcome": AgentOutcome.OK, "scrubbed_report": dependencies.report_scrubber(state.get("report") or "")}

    def finalize(state: AgentState) -> AgentState:
        return _finalize_state(state, dependencies, state.get("outcome") or AgentOutcome.OK)

    return {
        "guard": guard,
        "refuse": refuse,
        "retrieve_golden": retrieve_golden,
        "generate_sql": generate_sql,
        "schema_report": schema_report,
        "validate_sql": validate_sql,
        "self_correct": self_correct,
        "run_sql": run_sql,
        "no_data_report": no_data_report,
        "cost_refusal": cost_refusal,
        "failure_response": failure_response,
        "generate_report": report,
        "scrub_report": scrub,
        "finalize": finalize,
    }


def _route_after_guard(state: AgentState) -> NodeRoute:
    if state.get("outcome") == AgentOutcome.BLOCKED:
        return NodeRoute.REFUSE
    if state.get("outcome") == AgentOutcome.FAILED:
        return NodeRoute.FAILURE_RESPONSE
    if is_schema_question(state["question"]):
        return NodeRoute.SCHEMA_REPORT
    return NodeRoute.RETRIEVE_GOLDEN


def _route_after_generate_sql(state: AgentState) -> NodeRoute:
    return NodeRoute.FAILURE_RESPONSE if state.get("outcome") == AgentOutcome.FAILED else NodeRoute.VALIDATE_SQL


def _route_after_report(state: AgentState) -> NodeRoute:
    return NodeRoute.FAILURE_RESPONSE if state.get("outcome") == AgentOutcome.FAILED else NodeRoute.SCRUB_REPORT


def build_graph(
    *,
    dependencies: AgentDependencies | None = None,
    checkpointer: BaseCheckpointSaver[str] | None = None,
    use_checkpointer: bool = True,
) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    """Build and compile the synchronous LangGraph StateGraph."""

    deps = dependencies or AgentDependencies()
    saver = checkpointer
    if saver is None and use_checkpointer:
        saver = build_postgres_saver(setup=True)

    nodes = _build_nodes(deps)
    graph = StateGraph(AgentState)
    for name, node in nodes.items():
        graph.add_node(name, cast(Any, node))

    def route_after_validate(state: AgentState) -> NodeRoute:
        if not state.get("validation_error"):
            return NodeRoute.RUN_SQL
        return NodeRoute.SELF_CORRECT if _should_retry(state) else NodeRoute.FAILURE_RESPONSE

    def route_after_run(state: AgentState) -> NodeRoute:
        if state.get("outcome") == AgentOutcome.COST_EXCEEDED:
            return NodeRoute.COST_REFUSAL
        if state.get("last_error"):
            return NodeRoute.SELF_CORRECT if _should_retry(state) else NodeRoute.FAILURE_RESPONSE
        if not state.get("masked_result_rows"):
            return NodeRoute.NO_DATA_REPORT
        return NodeRoute.GENERATE_REPORT

    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", _route_after_guard)
    graph.add_edge("refuse", "finalize")
    graph.add_edge("schema_report", "finalize")
    graph.add_edge("retrieve_golden", "generate_sql")
    graph.add_conditional_edges("generate_sql", _route_after_generate_sql)
    graph.add_conditional_edges("validate_sql", route_after_validate)
    graph.add_edge("self_correct", "generate_sql")
    graph.add_conditional_edges("run_sql", route_after_run)
    graph.add_edge("no_data_report", "finalize")
    graph.add_edge("cost_refusal", "finalize")
    graph.add_edge("failure_response", "finalize")
    graph.add_conditional_edges("generate_report", _route_after_report)
    graph.add_edge("scrub_report", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=saver)


def close_graph_resources() -> None:
    """Close cached resources owned by the compiled agent graph."""

    close_checkpointer_pool()
