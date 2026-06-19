"""Markdown rendering for eval artifacts."""

from retail_agent.const import MAX_DEFAULT_LATENCY_SEC
from retail_agent.evaluation.models import EvalReport, ModelAggregate


def render_markdown_report(report: EvalReport) -> str:
    """Render the eval report as a Markdown table."""

    aggregates_by_model = {aggregate.model: aggregate for aggregate in report.aggregates}
    accuracy_leader = aggregates_by_model.get(report.winner or "")
    pinned_default = aggregates_by_model.get(report.pinned_default or "")

    lines = [
        "# Retail Agent A/B Eval Results",
        "",
        f"Generated at: {report.generated_at}",
        f"Ranking rule: {report.ranking_rule}",
        (
            "Accuracy leader: n/a"
            if accuracy_leader is None
            else f"Accuracy leader: {accuracy_leader.model} (correctness {accuracy_leader.mean_correctness:.3f})"
        ),
        _render_pinned_default_line(accuracy_leader, pinned_default),
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


def _render_pinned_default_line(
    accuracy_leader: ModelAggregate | None,
    pinned_default: ModelAggregate | None,
) -> str:
    if pinned_default is None:
        return (
            "Pinned default: n/a -- no ranked model is within the interactive latency SLA "
            f"(<= {MAX_DEFAULT_LATENCY_SEC:.0f}s)."
        )
    pinned_line = (
        f"Pinned default: {pinned_default.model} -- most accurate model within the interactive latency SLA "
        f"(<= {MAX_DEFAULT_LATENCY_SEC:.0f}s)"
    )
    if (
        accuracy_leader is not None
        and accuracy_leader.model != pinned_default.model
        and accuracy_leader.mean_latency_sec > MAX_DEFAULT_LATENCY_SEC
    ):
        pinned_line += (
            f"; {accuracy_leader.model} excluded as default "
            f"(mean latency {accuracy_leader.mean_latency_sec:.1f}s exceeds the budget)."
        )
    else:
        pinned_line += "."
    return pinned_line
