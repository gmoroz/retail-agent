"""Unit tests for the TraceCollector callback (PR-006, AC4).

A simulated ``LLMResult`` drives the callback directly (no network): tokens come from
``usage_metadata`` and cost from ``response_metadata["token_usage"]["cost"]``. The
cost-present path yields a float; the cost-absent path (a dev gateway that does not
honour ``usage:{include:true}``) yields ``None`` without error. Records accumulate
across calls and ``finalize`` folds them into one trace.
"""

from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from retail_agent.config import Settings
from retail_agent.services.llm import build_chat_model
from retail_agent.services.observability import TraceCollector

USAGE = {"input_tokens": 11, "output_tokens": 21, "total_tokens": 32}


def _response(cost: float | None) -> LLMResult:
    token_usage: dict[str, float] = {"prompt_tokens": 11, "completion_tokens": 21, "total_tokens": 32}
    if cost is not None:
        token_usage["cost"] = cost
    message = AIMessage(
        content="hi",
        usage_metadata=USAGE,
        response_metadata={"token_usage": token_usage},
    )
    return LLMResult(generations=[[ChatGeneration(message=message)]])


def _run_one_call(collector: TraceCollector, response: LLMResult) -> None:
    run_id = uuid4()
    serialized = {"kwargs": {"model": "deepseek/deepseek-v4-flash"}}
    collector.on_chat_model_start(serialized, [], run_id=run_id)
    collector.on_llm_end(response, run_id=run_id)


def test_collector_extracts_tokens_and_cost_when_present() -> None:
    collector = TraceCollector(trace_id="trace-1")

    _run_one_call(collector, _response(cost=7.1e-06))

    assert len(collector.records) == 1
    record = collector.records[0]
    assert record.prompt_tokens == 11
    assert record.completion_tokens == 21
    assert record.total_tokens == 32
    assert record.cost == pytest.approx(7.1e-06)
    assert record.model == "deepseek/deepseek-v4-flash"
    assert record.latency_sec >= 0.0
    assert record.error is None


def test_collector_cost_absent_yields_none_gracefully() -> None:
    collector = TraceCollector(trace_id="trace-2")

    _run_one_call(collector, _response(cost=None))

    record = collector.records[0]
    assert record.prompt_tokens == 11
    assert record.completion_tokens == 21
    assert record.cost is None
    assert collector.total_cost is None


def test_collector_accumulates_across_calls() -> None:
    collector = TraceCollector(trace_id="trace-3")

    _run_one_call(collector, _response(cost=1.0))
    _run_one_call(collector, _response(cost=2.5))

    assert collector.total_prompt_tokens == 22
    assert collector.total_completion_tokens == 42
    assert collector.total_cost == pytest.approx(3.5)


def test_collector_records_llm_error() -> None:
    collector = TraceCollector(trace_id="trace-4")
    run_id = uuid4()
    collector.on_chat_model_start({"kwargs": {"model": "m"}}, [], run_id=run_id)
    collector.on_llm_error(TimeoutError("upstream timeout"), run_id=run_id)

    record = collector.records[0]
    assert record.prompt_tokens == 0
    assert record.completion_tokens == 0
    assert record.cost is None
    assert record.error == "upstream timeout"
    assert collector.last_error == "upstream timeout"


def test_finalize_emits_trace() -> None:
    collector = TraceCollector(trace_id="trace-5")
    _run_one_call(collector, _response(cost=0.5))

    trace = collector.finalize(
        outcome="ok",
        total_latency_sec=1.25,
        bigquery_bytes=4096,
        self_correct_iterations=1,
    )

    assert trace.trace_id == "trace-5"
    assert trace.outcome == "ok"
    assert trace.total_latency_sec == 1.25
    assert trace.prompt_tokens == 11
    assert trace.completion_tokens == 21
    assert trace.total_tokens == 32
    assert trace.cost == pytest.approx(0.5)
    assert trace.llm_call_count == 1
    assert trace.bigquery_bytes == 4096
    assert trace.self_correct_iterations == 1
    assert trace.error is None


@pytest.mark.integration
def test_collector_fires_on_real_invoke() -> None:
    settings = Settings()
    collector = TraceCollector(trace_id="live-callback")
    model = build_chat_model(model="deepseek/deepseek-v4-flash", settings_provider=lambda: settings)

    model.invoke([HumanMessage(content="Reply with exactly one word: hello")], config={"callbacks": [collector]})

    assert len(collector.records) == 1
    record = collector.records[0]
    assert record.total_tokens > 0
    assert record.cost is not None
    assert record.error is None
