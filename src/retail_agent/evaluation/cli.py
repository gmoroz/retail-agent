"""Command-line interface for the eval package."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from retail_agent.const import AB_MODELS
from retail_agent.evaluation.paths import DEFAULT_GOLDEN_SET_PATH, DEFAULT_RESULTS_JSON_PATH, DEFAULT_RESULTS_MD_PATH
from retail_agent.evaluation.report import render_markdown_report
from retail_agent.evaluation.runner import rerank_eval_results, run_eval


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for ``python -m retail_agent.eval``."""

    parser = argparse.ArgumentParser(description="Run the retail-agent offline A/B eval harness.")
    parser.add_argument("--models", default=",".join(AB_MODELS), help="Comma-separated model slugs to evaluate.")
    parser.add_argument("--limit-questions", type=int, default=None, help="Optional prefix length for smoke runs.")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET_PATH)
    parser.add_argument("--results-json", type=Path, default=DEFAULT_RESULTS_JSON_PATH)
    parser.add_argument("--results-md", type=Path, default=DEFAULT_RESULTS_MD_PATH)
    parser.add_argument(
        "--rerank-from",
        type=Path,
        default=None,
        help="Load saved eval case rows and rewrite result artifacts without running models or BigQuery.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the eval CLI and write the Markdown summary to stdout."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.rerank_from is not None:
        report = rerank_eval_results(
            source_json_path=args.rerank_from,
            results_json_path=args.results_json,
            results_md_path=args.results_md,
        )
        sys.stdout.write(render_markdown_report(report))
        return 0

    model_slugs = tuple(slug.strip() for slug in args.models.split(",") if slug.strip())
    report = run_eval(
        model_slugs=model_slugs,
        question_limit=args.limit_questions,
        golden_set_path=args.golden_set,
        results_json_path=args.results_json,
        results_md_path=args.results_md,
    )
    sys.stdout.write(render_markdown_report(report))
    return 0
