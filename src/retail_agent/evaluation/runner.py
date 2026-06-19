"""Offline eval runner over the production LangGraph agent."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import cast

import openai

from retail_agent.agent.graph import AgentDependencies, build_graph
from retail_agent.agent.state import AgentState
from retail_agent.const import AB_MODELS
from retail_agent.evaluation.io import (
    assert_seed_and_holdout_disjoint,
    load_golden_questions,
    load_seed_trios,
    read_eval_report,
    write_report,
)
from retail_agent.evaluation.models import EvalCaseResult, EvalReport, GoldenQuestion
from retail_agent.evaluation.paths import DEFAULT_GOLDEN_SET_PATH, DEFAULT_RESULTS_JSON_PATH, DEFAULT_RESULTS_MD_PATH
from retail_agent.evaluation.ranking import RANKING_RULE, aggregate_model_results, rank_models
from retail_agent.evaluation.report import render_markdown_report
from retail_agent.evaluation.scoring import compare_result_sets, judge_report
from retail_agent.exceptions import RetailAgentError
from retail_agent.repositories import bigquery
from retail_agent.services.llm import build_chat_model

logger = logging.getLogger(__name__)

RATE_LIMIT_ATTEMPTS = 3
RATE_LIMIT_SLEEP_SEC = 8.0
RATE_LIMIT_MARKERS = ("429", "rate limit", "rate_limit", "too many requests")


def run_eval(
    *,
    model_slugs: tuple[str, ...] = AB_MODELS,
    question_limit: int | None = None,
    golden_set_path: Path = DEFAULT_GOLDEN_SET_PATH,
    results_json_path: Path = DEFAULT_RESULTS_JSON_PATH,
    results_md_path: Path = DEFAULT_RESULTS_MD_PATH,
) -> EvalReport:
    """Run the offline A/B harness and write JSON plus Markdown artifacts."""

    seed_trios = load_seed_trios()
    golden_questions = load_golden_questions(golden_set_path)
    assert_seed_and_holdout_disjoint(seed_trios, golden_questions)
    selected_questions = golden_questions[:question_limit] if question_limit is not None else golden_questions

    cases: list[EvalCaseResult] = []
    for model_slug in model_slugs:
        for question in selected_questions:
            cases.append(_run_case(model_slug, question))

    ranked = rank_models(aggregate_model_results(cases))
    report = EvalReport(
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        ranking_rule=RANKING_RULE,
        winner=ranked[0].model if ranked else None,
        pinned_default=ranked[0].model if ranked else None,
        aggregates=list(ranked),
        cases=cases,
    )
    write_report(report, results_json_path, results_md_path, render_markdown_report(report))
    return report


def rerank_eval_results(
    source_json_path: Path = DEFAULT_RESULTS_JSON_PATH,
    *,
    results_json_path: Path = DEFAULT_RESULTS_JSON_PATH,
    results_md_path: Path = DEFAULT_RESULTS_MD_PATH,
) -> EvalReport:
    """Rebuild eval artifacts from saved case rows without running the eval graph."""

    report = read_eval_report(source_json_path)
    ranked = rank_models(aggregate_model_results(report.cases))
    reranked = EvalReport(
        generated_at=report.generated_at,
        ranking_rule=RANKING_RULE,
        winner=ranked[0].model if ranked else None,
        pinned_default=ranked[0].model if ranked else None,
        aggregates=list(ranked),
        cases=report.cases,
    )
    write_report(reranked, results_json_path, results_md_path, render_markdown_report(reranked))
    return reranked


def _run_case(model_slug: str, question: GoldenQuestion) -> EvalCaseResult:
    started = time.perf_counter()
    generated_sql: str | None = None
    error: str | None = None
    outcome = "failed"
    correctness = 0.0
    quality = 0.0
    candidate_cost: float | None = None
    judge_cost: float | None = None
    judge_reason: str | None = None
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    try:
        state = _invoke_agent(model_slug, question.question)
        generated_sql = state.get("sql")
        outcome = str(state.get("outcome", "failed"))
        trace = _trace_from_state(state)
        candidate_cost = _optional_float(trace.get("cost"))
        prompt_tokens = _int_from_trace(trace.get("prompt_tokens"))
        completion_tokens = _int_from_trace(trace.get("completion_tokens"))
        total_tokens = _int_from_trace(trace.get("total_tokens"))
        if outcome == "ok" and generated_sql:
            generated_frame = bigquery.run_query(generated_sql)
            reference_frame = bigquery.run_query(question.reference_sql)
            comparison = compare_result_sets(generated_frame, reference_frame)
            correctness = 1.0 if comparison.matches else 0.0
            judge = judge_report(question.question, reference_frame, str(state.get("scrubbed_report", "")))
            quality = judge.score
            judge_cost = judge.cost
            judge_reason = judge.reason
        else:
            error = str(state.get("last_error") or state.get("scrubbed_report") or "agent did not return ok")
    except (
        RetailAgentError,
        openai.OpenAIError,
        RuntimeError,
        TimeoutError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        error = str(exc)
        logger.warning(
            "eval case failed",
            extra={"model": model_slug, "question_id": question.id, "error": error},
        )
    return EvalCaseResult(
        model=model_slug,
        question_id=question.id,
        category=question.category,
        question=question.question,
        outcome=outcome,
        correctness=correctness,
        quality=quality,
        latency_sec=time.perf_counter() - started,
        cost=candidate_cost,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        generated_sql=generated_sql,
        error=error,
        judge_cost=judge_cost,
        judge_reason=judge_reason,
    )


def _invoke_agent(model_slug: str, question: str) -> AgentState:
    dependencies = AgentDependencies(chat_model_builder=lambda: build_chat_model(model=model_slug))
    graph = build_graph(dependencies=dependencies, use_checkpointer=False)
    last_state: AgentState | None = None
    for attempt in range(1, RATE_LIMIT_ATTEMPTS + 1):
        state = cast(AgentState, graph.invoke({"question": question}))
        last_state = state
        last_error = str(state.get("last_error") or "")
        if state.get("outcome") != "failed" or not _looks_rate_limited(last_error):
            return state
        if attempt < RATE_LIMIT_ATTEMPTS:
            time.sleep(RATE_LIMIT_SLEEP_SEC)
    if last_state is None:
        raise RuntimeError("agent eval did not produce a state")
    return last_state


def _trace_from_state(state: AgentState) -> dict[str, object]:
    trace = state.get("run_trace")
    return trace if isinstance(trace, dict) else {}


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _int_from_trace(value: object) -> int:
    return int(value) if isinstance(value, int) else 0


def _looks_rate_limited(message: str) -> bool:
    lowered = message.casefold()
    return any(marker in lowered for marker in RATE_LIMIT_MARKERS)
