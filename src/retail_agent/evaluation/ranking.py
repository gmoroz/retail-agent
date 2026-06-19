"""Eval aggregation and deterministic model ranking."""

import math
from collections.abc import Iterable, Sequence

from retail_agent.const import QUALITY_BAND_EPSILON
from retail_agent.evaluation.models import EvalCaseResult, ModelAggregate

RANKING_RULE = (
    "correctness DESC, report quality band DESC (0.05 LLM-judge noise floor), "
    "mean cost ASC, mean latency ASC, model ASC"
)


def aggregate_model_results(cases: Sequence[EvalCaseResult]) -> list[ModelAggregate]:
    """Aggregate case-level eval rows by model."""

    aggregates: list[ModelAggregate] = []
    for model in sorted({case.model for case in cases}):
        model_cases = [case for case in cases if case.model == model]
        known_costs = [case.cost for case in model_cases if case.cost is not None]
        total_known_cost = sum(known_costs)
        total_cost = total_known_cost if known_costs else None
        aggregates.append(
            ModelAggregate(
                model=model,
                questions=len(model_cases),
                mean_correctness=_mean(case.correctness for case in model_cases),
                mean_quality=_mean(case.quality for case in model_cases),
                total_cost=total_cost,
                mean_cost=(total_known_cost / len(known_costs)) if known_costs else None,
                mean_latency_sec=_mean(case.latency_sec for case in model_cases),
                total_tokens=sum(case.total_tokens for case in model_cases),
            )
        )
    return aggregates


def rank_models(aggregates: Sequence[ModelAggregate]) -> list[ModelAggregate]:
    """Return PR-005 deterministic ordering with quality banded by judge noise."""

    return sorted(
        aggregates,
        key=lambda aggregate: (
            -aggregate.mean_correctness,
            -_quality_band_for_ranking(aggregate.mean_quality),
            _cost_for_ranking(aggregate.mean_cost),
            aggregate.mean_latency_sec,
            aggregate.model,
        ),
    )


def _mean(values: Iterable[float]) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0


def _cost_for_ranking(cost: float | None) -> float:
    return cost if cost is not None else math.inf


def _quality_band_for_ranking(quality: float) -> float:
    return math.floor((quality / QUALITY_BAND_EPSILON) + 0.5) * QUALITY_BAND_EPSILON
