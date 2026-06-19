"""Pydantic value objects for the offline eval harness."""

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    """Immutable pydantic base for eval value objects."""

    model_config = ConfigDict(frozen=True)


class SeedTrio(FrozenModel):
    """Seed Trio loaded from the eval seed set."""

    question: str
    sql: str
    report: str


class GoldenQuestion(FrozenModel):
    """Holdout eval question with a reference SQL query."""

    id: str
    category: str
    question: str
    reference_sql: str


class ComparisonResult(FrozenModel):
    """Canonical result-set comparison outcome."""

    matches: bool
    generated_rows: int
    reference_rows: int


class JudgeResult(FrozenModel):
    """LLM-as-judge score and accounting."""

    score: float
    reason: str
    cost: float | None


class EvalCaseResult(FrozenModel):
    """One model/question eval row."""

    model: str
    question_id: str
    category: str
    question: str
    outcome: str
    correctness: float
    quality: float
    latency_sec: float
    cost: float | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    generated_sql: str | None
    error: str | None
    judge_cost: float | None
    judge_reason: str | None


class ModelAggregate(FrozenModel):
    """Per-model aggregate metrics used for PR-005 ranking."""

    model: str
    questions: int
    mean_correctness: float
    mean_quality: float
    total_cost: float | None
    mean_cost: float | None
    mean_latency_sec: float
    total_tokens: int


class EvalReport(FrozenModel):
    """Full eval artifact written as JSON and Markdown."""

    generated_at: str
    ranking_rule: str
    winner: str | None
    pinned_default: str | None
    aggregates: list[ModelAggregate]
    cases: list[EvalCaseResult]
