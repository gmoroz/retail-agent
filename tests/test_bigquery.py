"""Tests for BigQuery repository I/O and service-layer cost guarding."""

import pandas as pd
import pytest
from google.api_core.exceptions import ServiceUnavailable

import retail_agent.repositories.bigquery as bq_repo
from retail_agent.const import ALLOWED_TABLES, MAX_BIGQUERY_BYTES_BILLED
from retail_agent.exceptions import BigQueryExecutionError, CostBudgetExceededError
from retail_agent.repositories.bigquery import (
    dry_run_bytes,
    introspect_schema,
    run_query,
)
from retail_agent.services.query_execution import QueryExecutionService


def test_query_execution_service_oversized_estimate_rejected() -> None:
    service = QueryExecutionService(
        dry_run_estimator=lambda sql: MAX_BIGQUERY_BYTES_BILLED + 1,
        query_runner=lambda sql: pd.DataFrame({"should_not_run": [1]}),
    )

    with pytest.raises(CostBudgetExceededError):
        service.execute("SELECT COUNT(*) FROM `bigquery-public-data.thelook_ecommerce`.orders")


def test_run_query_materialization_error_wrapped(monkeypatch: pytest.MonkeyPatch, settings: object) -> None:
    class RowsDouble:
        def to_dataframe(self, *, create_bqstorage_client: bool) -> pd.DataFrame:
            raise ServiceUnavailable("page fetch failed")

    class JobDouble:
        def result(self, *, timeout: float) -> RowsDouble:
            return RowsDouble()

    class ClientDouble:
        def query(self, sql: str, *, job_config: object) -> JobDouble:
            return JobDouble()

    monkeypatch.setattr(bq_repo, "get_client", lambda: ClientDouble())

    with pytest.raises(BigQueryExecutionError, match="query execution failed"):
        run_query("SELECT COUNT(*) FROM `bigquery-public-data.thelook_ecommerce`.orders")


@pytest.mark.integration
def test_dry_run_bytes_positive() -> None:
    sql = "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce`.order_items LIMIT 5"
    assert dry_run_bytes(sql) > 0


@pytest.mark.integration
def test_run_query_returns_dataframe() -> None:
    sql = "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce`.order_items LIMIT 5"
    frame = run_query(sql)
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 5


@pytest.mark.integration
def test_dry_run_malformed_raises_execution_error() -> None:
    with pytest.raises(BigQueryExecutionError):
        dry_run_bytes("SELECT FROM `bigquery-public-data.thelook_ecommerce`.orders")


@pytest.mark.integration
def test_introspect_schema_covers_allowlist() -> None:
    schema = introspect_schema()
    assert set(schema) == set(ALLOWED_TABLES)
    for columns in schema.values():
        assert columns, "every allowlist table should expose at least one column"
