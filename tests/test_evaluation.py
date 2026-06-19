"""Unit tests for offline eval comparison, ranking and holdout integrity."""

import os

import pandas as pd
import pytest

from retail_agent.const import AB_MODELS
from retail_agent.evaluation import (
    ModelAggregate,
    assert_seed_and_holdout_disjoint,
    compare_result_sets,
    load_golden_questions,
    load_seed_trios,
    rank_models,
    run_eval,
)
from retail_agent.services.text_utils import content_to_text, extract_json_object


def test_compare_result_sets_identical_rows_matches() -> None:
    generated = pd.DataFrame({"category": ["A"], "revenue": [10.25]})
    reference = pd.DataFrame({"category": ["A"], "revenue": [10.25]})

    comparison = compare_result_sets(generated, reference)

    assert comparison.matches
    assert comparison.generated_rows == 1
    assert comparison.reference_rows == 1


def test_compare_result_sets_identical_values_different_column_names_matches() -> None:
    generated = pd.DataFrame({"month": ["2024-01-01"], "revenue": [10.25]})
    reference = pd.DataFrame({"month": ["2024-01-01"], "completed_revenue": [10.25]})

    comparison = compare_result_sets(generated, reference)

    assert comparison.matches


def test_compare_result_sets_reference_subset_by_values_matches() -> None:
    generated = pd.DataFrame(
        {
            "id": [40426, 85246],
            "first_name": ["Ava", "Mia"],
            "last_name": ["Stone", "Park"],
            "total_spend": [1469.20, 1422.44],
        }
    )
    reference = pd.DataFrame({"user_id": [40426, 85246], "spend": [1469.20, 1422.44]})

    comparison = compare_result_sets(generated, reference)

    assert comparison.matches


def test_compare_result_sets_different_order_without_order_contract_matches() -> None:
    generated = pd.DataFrame({"category": ["B", "A"], "revenue": [20.0, 10.0]})
    reference = pd.DataFrame({"category": ["A", "B"], "revenue": [10.0, 20.0]})

    comparison = compare_result_sets(generated, reference)

    assert comparison.matches


def test_compare_result_sets_different_values_mismatches() -> None:
    generated = pd.DataFrame({"category": ["A"], "revenue": [10.0]})
    reference = pd.DataFrame({"category": ["A"], "revenue": [11.0]})

    comparison = compare_result_sets(generated, reference)

    assert not comparison.matches


def test_compare_result_sets_different_row_count_mismatches() -> None:
    generated = pd.DataFrame({"category": ["A", "B"], "revenue": [10.0, 20.0]})
    reference = pd.DataFrame({"category": ["A"], "revenue": [10.0]})

    comparison = compare_result_sets(generated, reference)

    assert not comparison.matches
    assert comparison.generated_rows == 2
    assert comparison.reference_rows == 1


def test_compare_result_sets_missing_reference_column_by_values_mismatches() -> None:
    generated = pd.DataFrame({"category": ["A"], "wrong_revenue": [9.0], "items": [1]})
    reference = pd.DataFrame({"category": ["A"], "revenue": [10.0]})

    comparison = compare_result_sets(generated, reference)

    assert not comparison.matches


def test_compare_result_sets_agent_missing_reference_column_count_mismatches() -> None:
    generated = pd.DataFrame({"category": ["A"], "revenue": [10.0]})
    reference = pd.DataFrame({"category": ["A"], "revenue": [10.0], "items": [1]})

    comparison = compare_result_sets(generated, reference)

    assert not comparison.matches
    assert comparison.generated_rows == 1
    assert comparison.reference_rows == 1


def test_compare_result_sets_float_rounding_matches() -> None:
    generated = pd.DataFrame({"metric": [1.12345611], "extra": ["ignored"]})
    reference = pd.DataFrame({"metric": [1.12345612]})

    comparison = compare_result_sets(generated, reference)

    assert comparison.matches


def test_rank_models_orders_by_pr005_metrics_and_cheaper_tie_break() -> None:
    aggregates = [
        ModelAggregate(
            model="slower",
            questions=2,
            mean_correctness=1.0,
            mean_quality=0.9,
            total_cost=0.30,
            mean_cost=0.15,
            mean_latency_sec=3.0,
            total_tokens=100,
        ),
        ModelAggregate(
            model="better_quality",
            questions=2,
            mean_correctness=1.0,
            mean_quality=0.95,
            total_cost=0.50,
            mean_cost=0.25,
            mean_latency_sec=4.0,
            total_tokens=100,
        ),
        ModelAggregate(
            model="cheaper",
            questions=2,
            mean_correctness=1.0,
            mean_quality=0.9,
            total_cost=0.20,
            mean_cost=0.10,
            mean_latency_sec=5.0,
            total_tokens=100,
        ),
        ModelAggregate(
            model="less_correct",
            questions=2,
            mean_correctness=0.5,
            mean_quality=1.0,
            total_cost=0.01,
            mean_cost=0.005,
            mean_latency_sec=1.0,
            total_tokens=100,
        ),
    ]

    ranked = rank_models(aggregates)

    assert [aggregate.model for aggregate in ranked] == ["better_quality", "cheaper", "slower", "less_correct"]


def test_rank_models_uses_cost_when_quality_is_inside_judge_noise_band() -> None:
    aggregates = [
        ModelAggregate(
            model="z-ai/glm-5.2",
            questions=20,
            mean_correctness=0.8,
            mean_quality=0.635,
            total_cost=0.134470,
            mean_cost=0.006724,
            mean_latency_sec=44.87,
            total_tokens=46938,
        ),
        ModelAggregate(
            model="deepseek/deepseek-v4-flash",
            questions=20,
            mean_correctness=0.8,
            mean_quality=0.633,
            total_cost=0.006836,
            mean_cost=0.000342,
            mean_latency_sec=24.67,
            total_tokens=41875,
        ),
    ]

    ranked = rank_models(aggregates)

    assert [aggregate.model for aggregate in ranked] == ["deepseek/deepseek-v4-flash", "z-ai/glm-5.2"]


def test_rank_models_uses_quality_when_difference_exceeds_judge_noise_band() -> None:
    aggregates = [
        ModelAggregate(
            model="cheaper",
            questions=20,
            mean_correctness=0.8,
            mean_quality=0.60,
            total_cost=0.01,
            mean_cost=0.0005,
            mean_latency_sec=10.0,
            total_tokens=1000,
        ),
        ModelAggregate(
            model="better_quality",
            questions=20,
            mean_correctness=0.8,
            mean_quality=0.66,
            total_cost=0.20,
            mean_cost=0.0100,
            mean_latency_sec=20.0,
            total_tokens=1000,
        ),
    ]

    ranked = rank_models(aggregates)

    assert [aggregate.model for aggregate in ranked] == ["better_quality", "cheaper"]


def test_judge_json_helper_extracts_first_balanced_object() -> None:
    text = 'notes {"score": 0.75, "meta": {"nested": true}, "reason": "ok"} trailing {"score": 0}'

    assert extract_json_object(content_to_text(text)) == '{"score": 0.75, "meta": {"nested": true}, "reason": "ok"}'


def test_seed_and_golden_question_sets_are_disjoint() -> None:
    seeds = load_seed_trios()
    questions = load_golden_questions()

    assert len(seeds) == 10
    assert len(questions) == 20
    assert_seed_and_holdout_disjoint(seeds, questions)


@pytest.mark.integration
def test_full_ab_eval_runs_when_explicitly_enabled() -> None:
    if os.getenv("RUN_FULL_EVAL") != "1":
        pytest.skip("set RUN_FULL_EVAL=1 to run the full 4x20 paid eval")

    report = run_eval(model_slugs=AB_MODELS)

    assert report.winner in AB_MODELS
    assert len(report.cases) == len(AB_MODELS) * 20
