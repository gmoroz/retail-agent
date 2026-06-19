"""Analytical SQL execution with the service-layer BigQuery cost guard."""

from collections.abc import Callable

import pandas as pd
from pydantic import BaseModel, ConfigDict
from sqlglot import exp

from retail_agent.const import MAX_BIGQUERY_BYTES_BILLED, MAX_RESULT_ROWS
from retail_agent.exceptions import CostBudgetExceededError
from retail_agent.repositories import bigquery
from retail_agent.services.safety import mask_data
from retail_agent.services.sql_validation import validate_read_only_sql


def _literal_limit_value(limit: exp.Limit | None) -> int | None:
    if limit is None:
        return None
    expression = limit.args.get("expression")
    if not isinstance(expression, exp.Literal) or expression.is_string:
        return None
    raw_value = str(expression.this)
    return int(raw_value) if raw_value.isdecimal() else None


def _bounded_execution_sql(sql: str, max_result_rows: int) -> str:
    statement = validate_read_only_sql(sql)
    row_transfer_limit = max_result_rows + 1
    current_limit = _literal_limit_value(statement.args.get("limit"))
    if current_limit is not None and current_limit <= row_transfer_limit:
        return statement.sql(dialect="bigquery")
    bounded_statement = statement.copy()
    bounded_statement.set("limit", exp.Limit(expression=exp.Literal.number(row_transfer_limit)))
    return bounded_statement.sql(dialect="bigquery")


class QueryExecutionResult(BaseModel):
    """Masked query rows and their BigQuery dry-run byte estimate."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    masked_frame: pd.DataFrame
    estimated_bytes: int
    total_rows: int
    truncated: bool


class QueryExecutionService(BaseModel):
    """Execute validated analytical SQL behind a dry-run cost guard."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    dry_run_estimator: Callable[[str], int] = bigquery.dry_run_bytes
    query_runner: Callable[[str], pd.DataFrame] = bigquery.run_query
    data_masker: Callable[[pd.DataFrame], pd.DataFrame] = mask_data
    max_bytes_billed: int = MAX_BIGQUERY_BYTES_BILLED
    max_result_rows: int = MAX_RESULT_ROWS

    def execute(self, sql: str) -> QueryExecutionResult:
        """Run ``sql`` and return masked rows after enforcing the byte cap."""

        bounded_sql = _bounded_execution_sql(sql, self.max_result_rows)
        estimated = self.dry_run_estimator(bounded_sql)
        if estimated > self.max_bytes_billed:
            raise CostBudgetExceededError(
                f"estimated {estimated} bytes exceeds cap {self.max_bytes_billed}",
                estimated_bytes=estimated,
                max_bytes=self.max_bytes_billed,
            )
        masked = self.data_masker(self.query_runner(bounded_sql))
        total_rows = len(masked)
        truncated = total_rows > self.max_result_rows
        if truncated:
            masked = masked.head(self.max_result_rows).copy()
        return QueryExecutionResult(
            masked_frame=masked,
            estimated_bytes=estimated,
            total_rows=total_rows,
            truncated=truncated,
        )
