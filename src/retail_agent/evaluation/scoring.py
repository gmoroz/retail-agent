"""Result-set comparison and LLM judge scoring."""

import json
import math
import time
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from itertools import permutations
from typing import cast

import openai
import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from retail_agent.evaluation.models import ComparisonResult, JudgeResult
from retail_agent.services.llm import build_chat_model
from retail_agent.services.text_utils import content_to_text, extract_json_object

FLOAT_PRECISION = 6
RATE_LIMIT_ATTEMPTS = 3
RATE_LIMIT_SLEEP_SEC = 8.0

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial evaluator of retail analytics answers. Score only the report, "
    "not the SQL. Return strict JSON with a numeric score field from 0 to 1 and a short "
    "reason field. Rubric: 1.0 means the answer directly addresses the question, uses "
    "only supplied result facts, explains the business meaning clearly, and avoids SQL "
    "jargon; 0.5 means partially useful but missing important context; 0.0 means wrong, "
    "unsupported, empty, or not an answer."
)
JUDGE_USER_TEMPLATE = """Question:
{question}

Reference result:
{reference_rows}

Candidate report:
{report}

Return JSON only."""


def compare_result_sets(
    generated: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    order_sensitive: bool = False,
) -> ComparisonResult:
    """Compare result sets using reference-subset semantics."""

    generated_row_count = len(generated)
    reference_row_count = len(reference)
    if generated_row_count != reference_row_count or len(generated.columns) < len(reference.columns):
        return ComparisonResult(
            matches=False,
            generated_rows=generated_row_count,
            reference_rows=reference_row_count,
        )
    reference_rows = _canonical_rows(reference)
    if not order_sensitive:
        reference_rows = sorted(reference_rows, key=_row_sort_key)
    for column_mapping in _candidate_column_mappings(generated, reference):
        generated_rows = _canonical_rows(generated.iloc[:, list(column_mapping)])
        if not order_sensitive:
            generated_rows = sorted(generated_rows, key=_row_sort_key)
        if generated_rows == reference_rows:
            return ComparisonResult(
                matches=True,
                generated_rows=generated_row_count,
                reference_rows=reference_row_count,
            )
    return ComparisonResult(
        matches=False,
        generated_rows=generated_row_count,
        reference_rows=reference_row_count,
    )


def judge_report(question: str, reference_frame: pd.DataFrame, report: str) -> JudgeResult:
    """Score a candidate report with the fixed OpenRouter judge model."""

    judge_model = build_chat_model(for_judge=True)
    reference_rows = json.dumps(_jsonable_rows(reference_frame.head(20)), default=str)
    last_error: str | None = None
    for attempt in range(1, RATE_LIMIT_ATTEMPTS + 1):
        try:
            response = judge_model.invoke(
                [
                    SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                    HumanMessage(
                        content=JUDGE_USER_TEMPLATE.format(
                            question=question,
                            reference_rows=reference_rows,
                            report=report,
                        )
                    ),
                ]
            )
            payload = json.loads(extract_json_object(content_to_text(response.content)))
            if not isinstance(payload, dict):
                raise ValueError("judge response must be a JSON object")
            score = float(payload.get("score", 0.0))
            reason = str(payload.get("reason", ""))
            token_usage = response.response_metadata.get("token_usage", {})
            cost = _optional_float(token_usage.get("cost")) if isinstance(token_usage, dict) else None
            return JudgeResult(score=max(0.0, min(1.0, score)), reason=reason, cost=cost)
        except openai.RateLimitError as exc:
            last_error = str(exc)
            if attempt < RATE_LIMIT_ATTEMPTS:
                time.sleep(RATE_LIMIT_SLEEP_SEC)
        except (openai.OpenAIError, RuntimeError, TimeoutError, ValueError, TypeError) as exc:
            last_error = str(exc)
            break
    return JudgeResult(score=0.0, reason=last_error or "judge failed", cost=None)


def _canonical_rows(frame: pd.DataFrame) -> list[tuple[object, ...]]:
    normalized = frame.astype(object).where(pd.notna(frame), None)
    rows: list[tuple[object, ...]] = []
    for record in normalized.itertuples(index=False, name=None):
        rows.append(tuple(_normalize_value(value) for value in record))
    return rows


def _candidate_column_mappings(generated: pd.DataFrame, reference: pd.DataFrame) -> Iterable[tuple[int, ...]]:
    generated_value_sets = [
        _canonical_column_values(generated, column_index) for column_index in range(len(generated.columns))
    ]
    reference_value_sets = [
        _canonical_column_values(reference, column_index) for column_index in range(len(reference.columns))
    ]
    candidate_groups: list[list[int]] = []
    for reference_values in reference_value_sets:
        candidates = [
            generated_index
            for generated_index, generated_values in enumerate(generated_value_sets)
            if generated_values == reference_values
        ]
        if not candidates:
            return ()
        candidate_groups.append(candidates)
    if not candidate_groups:
        return ((),)
    return (
        mapping
        for mapping in permutations(range(len(generated.columns)), len(reference.columns))
        if all(
            generated_index in candidate_groups[reference_index]
            for reference_index, generated_index in enumerate(mapping)
        )
    )


def _canonical_column_values(frame: pd.DataFrame, column_index: int) -> tuple[object, ...]:
    values = [
        _normalize_value(value)
        for value in frame.iloc[:, column_index].astype(object).where(pd.notna(frame.iloc[:, column_index]), None)
    ]
    return tuple(sorted(values, key=lambda value: json.dumps(value, sort_keys=True, default=str)))


def _jsonable_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    normalized = frame.astype(object).where(pd.notna(frame), None)
    records = cast(list[dict[str, object]], normalized.to_dict(orient="records"))
    return [{key: _normalize_value(value) for key, value in record.items()} for record in records]


def _normalize_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return round(value, FLOAT_PRECISION)
    if isinstance(value, Decimal):
        return round(float(value), FLOAT_PRECISION)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _row_sort_key(row: tuple[object, ...]) -> str:
    return json.dumps(row, sort_keys=True, default=str)


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None
