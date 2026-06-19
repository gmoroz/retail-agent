"""Per-run observability for the agent (PR-006, AC4).

A :class:`TraceCollector` is a LangChain callback handler attached to a single agent
run. It records every chat-model call -- prompt/completion tokens from
``usage_metadata`` and the charged cost from ``response_metadata["token_usage"]["cost"]``
(read directly from OpenRouter's ``usage:{include:true}`` response, PR-006, never
self-computed), plus latency -- and accumulates them under one ``trace_id``.
:meth:`TraceCollector.finalize` folds in run-level facts the graph owns (BigQuery bytes,
self-correct iterations, outcome, total latency) and emits one structured log line.

Logging goes through stdlib ``logging`` with a JSON formatter so traces are machine
parsable; :func:`configure_logging` wires it once from the CLI.
"""

import json
import logging
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

LOG_RECORD_RESERVED = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Serialize every log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in LOG_RECORD_RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Attach a JSON-formatted stream handler to the root logger once."""

    root = logging.getLogger()
    if any(
        isinstance(handler, logging.StreamHandler) and isinstance(handler.formatter, JsonFormatter)
        for handler in root.handlers
    ):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


class LlmCallRecord(BaseModel):
    """Metrics captured for a single chat-model call."""

    model_config = ConfigDict(frozen=True)

    latency_sec: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float | None
    model: str | None
    error: str | None


class RunTrace(BaseModel):
    """Final trace for one agent run, logged and returned to the caller."""

    model_config = ConfigDict(frozen=True)

    trace_id: str
    outcome: str
    total_latency_sec: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float | None
    llm_call_count: int
    bigquery_bytes: int | None
    self_correct_iterations: int
    error: str | None


def _coerce_int(value: object) -> int:
    return int(value) if isinstance(value, int) else 0


def _extract_usage(response: LLMResult) -> tuple[int, int, int, float | None]:
    generation = response.generations[0][0]
    message = getattr(generation, "message", None)
    usage = getattr(message, "usage_metadata", None) if message else None
    usage_map = usage if isinstance(usage, Mapping) else {}
    response_metadata = getattr(message, "response_metadata", None) if message else None
    response_meta_map = response_metadata if isinstance(response_metadata, Mapping) else {}
    token_usage = response_meta_map.get("token_usage")
    token_usage_map = token_usage if isinstance(token_usage, Mapping) else {}

    prompt_tokens = _coerce_int(usage_map.get("input_tokens") or token_usage_map.get("prompt_tokens"))
    completion_tokens = _coerce_int(usage_map.get("output_tokens") or token_usage_map.get("completion_tokens"))
    total_tokens = _coerce_int(usage_map.get("total_tokens") or token_usage_map.get("total_tokens"))
    cost_raw = token_usage_map.get("cost")
    cost = float(cost_raw) if isinstance(cost_raw, int | float) else None
    return prompt_tokens, completion_tokens, total_tokens, cost


def _model_from_serialized(serialized: Mapping[str, object]) -> str | None:
    kwargs = serialized.get("kwargs")
    if isinstance(kwargs, Mapping):
        for key in ("model", "model_name"):
            value = kwargs.get(key)
            if isinstance(value, str):
                return value
    name = serialized.get("name")
    return name if isinstance(name, str) else None


class TraceCollector(BaseCallbackHandler):
    """Accumulate LLM-call metrics for one agent run under a shared ``trace_id``."""

    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or uuid4().hex
        self._starts: dict[UUID, float] = {}
        self._models: dict[UUID, str | None] = {}
        self.records: list[LlmCallRecord] = []

    def on_chat_model_start(  # type: ignore[override]
        self,
        serialized: dict[str, Any],
        _messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        _parent_run_id: UUID | None = None,
        _tags: list[str] | None = None,
        _metadata: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> None:
        self._starts[run_id] = time.perf_counter()
        self._models[run_id] = _model_from_serialized(serialized)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        _parent_run_id: UUID | None = None,
        _tags: list[str] | None = None,
        **_kwargs: Any,
    ) -> None:
        started = self._starts.pop(run_id, None)
        latency = time.perf_counter() - started if started is not None else 0.0
        if response.generations and response.generations[0]:
            prompt_tokens, completion_tokens, total_tokens, cost = _extract_usage(response)
        else:
            prompt_tokens, completion_tokens, total_tokens, cost = 0, 0, 0, None
        self.records.append(
            LlmCallRecord(
                latency_sec=latency,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                model=self._models.pop(run_id, None),
                error=None,
            )
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        _parent_run_id: UUID | None = None,
        _tags: list[str] | None = None,
        **_kwargs: Any,
    ) -> None:
        started = self._starts.pop(run_id, None)
        latency = time.perf_counter() - started if started is not None else 0.0
        self.records.append(
            LlmCallRecord(
                latency_sec=latency,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost=None,
                model=self._models.pop(run_id, None),
                error=str(error),
            )
        )

    @property
    def total_cost(self) -> float | None:
        known = [record.cost for record in self.records if record.cost is not None]
        return sum(known) if known else None

    @property
    def total_prompt_tokens(self) -> int:
        return sum(record.prompt_tokens for record in self.records)

    @property
    def total_completion_tokens(self) -> int:
        return sum(record.completion_tokens for record in self.records)

    def finalize(
        self,
        *,
        outcome: str,
        total_latency_sec: float,
        bigquery_bytes: int | None = None,
        self_correct_iterations: int = 0,
        error: str | None = None,
    ) -> RunTrace:
        """Freeze the run trace, log it, and return it to the caller."""

        trace = RunTrace(
            trace_id=self.trace_id,
            outcome=outcome,
            total_latency_sec=total_latency_sec,
            prompt_tokens=self.total_prompt_tokens,
            completion_tokens=self.total_completion_tokens,
            total_tokens=self.total_prompt_tokens + self.total_completion_tokens,
            cost=self.total_cost,
            llm_call_count=len(self.records),
            bigquery_bytes=bigquery_bytes,
            self_correct_iterations=self_correct_iterations,
            error=error or self.last_error,
        )
        logger.info("agent run trace", extra={"trace": _trace_to_dict(trace)})
        return trace

    @property
    def last_error(self) -> str | None:
        for record in reversed(self.records):
            if record.error is not None:
                return record.error
        return None


def _trace_to_dict(trace: RunTrace) -> dict[str, object]:
    return trace.model_dump(mode="json")
