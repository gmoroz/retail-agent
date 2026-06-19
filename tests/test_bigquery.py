"""Tests for BigQuery repository I/O and service-layer cost guarding."""

import pandas as pd
import pytest
from google.api_core.exceptions import ServiceUnavailable

import retail_agent.repositories.bigquery as bq_repo
from retail_agent.const import MAX_BIGQUERY_BYTES_BILLED, THELOOK_DATASET, THELOOK_TABLES
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


def test_query_execution_service_truncates_rows_above_cap() -> None:
    service = QueryExecutionService(
        dry_run_estimator=lambda sql: 1024,
        query_runner=lambda sql: pd.DataFrame({"user_id": [10, 20, 30], "orders": [1, 2, 3]}),
        max_result_rows=2,
    )

    execution = service.execute("SELECT user_id, orders FROM `bigquery-public-data.thelook_ecommerce`.users")

    assert len(execution.masked_frame) == 2
    assert execution.masked_frame["user_id"].tolist() == [10, 20]
    assert execution.masked_frame["orders"].tolist() == [1, 2]
    assert execution.total_rows == 3
    assert execution.truncated


def test_query_execution_service_keeps_rows_at_or_below_cap() -> None:
    source_frame = pd.DataFrame({"order_id": [10, 20], "orders": [1, 2]})
    service = QueryExecutionService(
        dry_run_estimator=lambda sql: 1024,
        query_runner=lambda sql: source_frame,
        max_result_rows=2,
    )

    execution = service.execute("SELECT order_id, orders FROM `bigquery-public-data.thelook_ecommerce`.orders")

    pd.testing.assert_frame_equal(execution.masked_frame, source_frame)
    assert execution.total_rows == 2
    assert not execution.truncated


def test_query_execution_service_adds_transfer_limit_when_missing() -> None:
    observed_sql: list[str] = []

    def record_dry_run(sql: str) -> int:
        observed_sql.append(sql)
        return 1024

    def record_run(sql: str) -> pd.DataFrame:
        observed_sql.append(sql)
        return pd.DataFrame({"order_id": [10, 20, 30]})

    service = QueryExecutionService(
        dry_run_estimator=record_dry_run,
        query_runner=record_run,
        max_result_rows=2,
    )

    execution = service.execute("SELECT order_id FROM `bigquery-public-data.thelook_ecommerce`.orders")

    assert observed_sql == [
        "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce.orders` LIMIT 3",
        "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce.orders` LIMIT 3",
    ]
    assert execution.truncated
    assert len(execution.masked_frame) == 2


def test_query_execution_service_preserves_smaller_user_limit() -> None:
    observed_sql: list[str] = []

    def record_dry_run(sql: str) -> int:
        observed_sql.append(sql)
        return 1024

    def record_run(sql: str) -> pd.DataFrame:
        observed_sql.append(sql)
        return pd.DataFrame({"order_id": [10]})

    service = QueryExecutionService(
        dry_run_estimator=record_dry_run,
        query_runner=record_run,
        max_result_rows=5,
    )

    execution = service.execute("SELECT order_id FROM `bigquery-public-data.thelook_ecommerce`.orders LIMIT 2")

    assert observed_sql == [
        "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce.orders` LIMIT 2",
        "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce.orders` LIMIT 2",
    ]
    assert not execution.truncated


def test_query_execution_service_replaces_larger_user_limit() -> None:
    observed_sql: list[str] = []

    def record_dry_run(sql: str) -> int:
        observed_sql.append(sql)
        return 1024

    def record_run(sql: str) -> pd.DataFrame:
        observed_sql.append(sql)
        return pd.DataFrame({"order_id": [10, 20, 30]})

    service = QueryExecutionService(
        dry_run_estimator=record_dry_run,
        query_runner=record_run,
        max_result_rows=2,
    )

    execution = service.execute("SELECT order_id FROM `bigquery-public-data.thelook_ecommerce`.orders LIMIT 20")

    assert observed_sql == [
        "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce.orders` LIMIT 3",
        "SELECT order_id FROM `bigquery-public-data.thelook_ecommerce.orders` LIMIT 3",
    ]
    assert execution.truncated


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
    assert set(schema) == {f"{THELOOK_DATASET}.{table}" for table in THELOOK_TABLES}
    for columns in schema.values():
        assert columns, "every allowlist table should expose at least one column"
