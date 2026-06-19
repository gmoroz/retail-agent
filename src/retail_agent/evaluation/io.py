"""Eval artifact loading, validation and persistence."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from retail_agent.evaluation.models import EvalReport, GoldenQuestion, SeedTrio
from retail_agent.evaluation.paths import DEFAULT_GOLDEN_SET_PATH, DEFAULT_SEED_PATH
from retail_agent.repositories import golden_bucket
from retail_agent.repositories.golden_bucket import GoldenTrioSeed


def load_seed_trios(path: Path = DEFAULT_SEED_PATH) -> list[SeedTrio]:
    """Load seed Trios from the repository eval artifact."""

    payload = _read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a list")
    trios: list[SeedTrio] = []
    for raw_trio in payload:
        if not isinstance(raw_trio, dict):
            raise ValueError(f"{path} contains a non-object seed trio")
        raw_map = cast(dict[object, object], raw_trio)
        trios.append(
            SeedTrio(
                question=_required_str(raw_map, "question", path),
                sql=_required_str(raw_map, "sql", path),
                report=_required_str(raw_map, "report", path),
            )
        )
    return trios


def load_golden_questions(path: Path = DEFAULT_GOLDEN_SET_PATH) -> list[GoldenQuestion]:
    """Load holdout eval questions from the repository eval artifact."""

    payload = _read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a list")
    questions: list[GoldenQuestion] = []
    for raw_question in payload:
        if not isinstance(raw_question, dict):
            raise ValueError(f"{path} contains a non-object golden question")
        raw_map = cast(dict[object, object], raw_question)
        questions.append(
            GoldenQuestion(
                id=_required_str(raw_map, "id", path),
                category=_required_str(raw_map, "category", path),
                question=_required_str(raw_map, "question", path),
                reference_sql=_required_str(raw_map, "reference_sql", path),
            )
        )
    return questions


def assert_seed_and_holdout_disjoint(
    seed_trios: Sequence[SeedTrio],
    golden_questions: Sequence[GoldenQuestion],
) -> None:
    """Raise when seed and holdout question texts overlap (PR-003)."""

    seed_questions = {_normalize_question(trio.question) for trio in seed_trios}
    holdout_questions = {_normalize_question(question.question) for question in golden_questions}
    overlap = sorted(seed_questions & holdout_questions)
    if overlap:
        raise ValueError(f"seed and holdout questions overlap: {overlap}")


def ingest_seed_trios(path: Path = DEFAULT_SEED_PATH) -> int:
    """Load seed Trios, embed them and insert them into the Golden bucket."""

    seeds = load_seed_trios(path)
    return golden_bucket.ingest_trios(
        [GoldenTrioSeed(question=seed.question, sql=seed.sql, report=seed.report) for seed in seeds]
    )


def write_report(report: EvalReport, json_path: Path, markdown_path: Path, markdown: str) -> None:
    """Write eval JSON and Markdown artifacts."""

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report_to_dict(report), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    markdown_path.write_text(markdown, encoding="utf-8")


def read_eval_report(path: Path) -> EvalReport:
    """Read a saved eval JSON artifact."""

    return EvalReport.model_validate(_read_json(path))


def report_to_dict(report: EvalReport) -> dict[str, object]:
    """Convert an eval report to a JSON-serializable dictionary."""

    return {
        "generated_at": report.generated_at,
        "ranking_rule": report.ranking_rule,
        "winner": report.winner,
        "pinned_default": report.pinned_default,
        "aggregates": [aggregate.model_dump(mode="json") for aggregate in report.aggregates],
        "cases": [case.model_dump(mode="json") for case in report.cases],
    }


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _required_str(payload: dict[object, object], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} entry missing non-empty {key}")
    return value


def _normalize_question(question: str) -> str:
    return " ".join(question.strip().casefold().split())
