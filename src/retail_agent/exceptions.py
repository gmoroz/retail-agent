"""Domain-specific exceptions.

Flat hierarchy under :class:`RetailAgentError`: every error inherits directly from
the base, no extra levels. Services raise these instead of bare ``Exception`` so
callers (graph nodes, CLI) can branch on concrete failure modes.
"""


class RetailAgentError(Exception):
    """Base class for all retail-agent domain errors."""


class SqlValidationError(RetailAgentError):
    """Raised when generated SQL fails read-only AST validation.

    Covers parse failure, a read-only deny-list hit (DML/DDL), or a non-select
    top-level statement.
    """


class MultiStatementError(RetailAgentError):
    """Raised when the parsed SQL contains more than one statement (PR-001)."""


class DisallowedTableError(RetailAgentError):
    """Raised when a referenced table is not in the allowlist (PR-002).

    Includes the mixed-table case: one allowed table plus an external one still
    fails, because the whole table set must be a subset of the allowlist.
    """


class CostBudgetExceededError(RetailAgentError):
    """Raised when a BigQuery dry run estimates bytes above the fixed cap."""

    def __init__(self, message: str, *, estimated_bytes: int | None = None, max_bytes: int | None = None) -> None:
        super().__init__(message)
        self.estimated_bytes = estimated_bytes
        self.max_bytes = max_bytes


class BigQueryExecutionError(RetailAgentError):
    """Raised when a validated query fails during BigQuery execution."""


class EmbeddingError(RetailAgentError):
    """Raised when an OpenRouter embedding request fails or returns the wrong dimension."""


class GoldenBucketError(RetailAgentError):
    """Raised on Golden-bucket (pgvector) ingest or retrieval failures."""
