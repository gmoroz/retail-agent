"""Public API for the offline A/B eval harness."""

from retail_agent.evaluation.cli import build_arg_parser, main
from retail_agent.evaluation.io import (
    assert_seed_and_holdout_disjoint,
    ingest_seed_trios,
    load_golden_questions,
    load_seed_trios,
)
from retail_agent.evaluation.models import (
    ComparisonResult,
    EvalCaseResult,
    EvalReport,
    GoldenQuestion,
    JudgeResult,
    ModelAggregate,
    SeedTrio,
)
from retail_agent.evaluation.paths import (
    DEFAULT_GOLDEN_SET_PATH,
    DEFAULT_RESULTS_JSON_PATH,
    DEFAULT_RESULTS_MD_PATH,
    DEFAULT_SEED_PATH,
)
from retail_agent.evaluation.ranking import aggregate_model_results, rank_models, select_pinned_default_model
from retail_agent.evaluation.report import render_markdown_report
from retail_agent.evaluation.runner import rerank_eval_results, run_eval
from retail_agent.evaluation.scoring import compare_result_sets

__all__ = [
    "DEFAULT_GOLDEN_SET_PATH",
    "DEFAULT_RESULTS_JSON_PATH",
    "DEFAULT_RESULTS_MD_PATH",
    "DEFAULT_SEED_PATH",
    "ComparisonResult",
    "EvalCaseResult",
    "EvalReport",
    "GoldenQuestion",
    "JudgeResult",
    "ModelAggregate",
    "SeedTrio",
    "aggregate_model_results",
    "assert_seed_and_holdout_disjoint",
    "build_arg_parser",
    "compare_result_sets",
    "ingest_seed_trios",
    "load_golden_questions",
    "load_seed_trios",
    "main",
    "rank_models",
    "render_markdown_report",
    "rerank_eval_results",
    "run_eval",
    "select_pinned_default_model",
]
