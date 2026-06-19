"""Markdown rendering for eval artifacts."""

from retail_agent.evaluation.models import EvalReport


def render_markdown_report(report: EvalReport) -> str:
    """Render the eval report as a Markdown table."""

    lines = [
        "# Retail Agent A/B Eval Results",
        "",
        f"Generated at: {report.generated_at}",
        f"Ranking rule: {report.ranking_rule}",
        f"Winner / pinned default: {report.winner or 'n/a'}",
        "",
        "| Model | Questions | Correctness | Quality | Total cost | Mean cost | Mean latency | Tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for aggregate in report.aggregates:
        lines.append(
            "| "
            f"{aggregate.model} | "
            f"{aggregate.questions} | "
            f"{aggregate.mean_correctness:.3f} | "
            f"{aggregate.mean_quality:.3f} | "
            f"{_format_optional_float(aggregate.total_cost, 6)} | "
            f"{_format_optional_float(aggregate.mean_cost, 6)} | "
            f"{aggregate.mean_latency_sec:.2f}s | "
            f"{aggregate.total_tokens} |"
        )
    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Model | Question | Outcome | Correct | Quality | Cost | Latency | Error |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for case in report.cases:
        lines.append(
            "| "
            f"{case.model} | "
            f"{case.question_id} | "
            f"{case.outcome} | "
            f"{case.correctness:.0f} | "
            f"{case.quality:.3f} | "
            f"{_format_optional_float(case.cost, 6)} | "
            f"{case.latency_sec:.2f}s | "
            f"{(case.error or '').replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def _format_optional_float(value: float | None, precision: int) -> str:
    return "n/a" if value is None else f"{value:.{precision}f}"
