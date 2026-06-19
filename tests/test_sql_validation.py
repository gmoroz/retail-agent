"""Unit tests for read-only SQL validation (PR-001/002/008).

Grounded in the verified sqlglot 30.11.0 parse behaviour: DML/DDL parse to their
own nodes, ``SELECT 1;`` stays a single statement, a trailing ``; DROP`` produces
two, top-level ``UNION ALL`` parses to ``exp.Union`` (not ``exp.Select``), and CTE
references appear as ``exp.Table`` nodes that must be excluded.
"""

import pytest
from sqlglot import exp

from retail_agent.exceptions import (
    DisallowedTableError,
    MultiStatementError,
    SqlValidationError,
)
from retail_agent.services.sql_validation import validate_read_only_sql

DS = "`bigquery-public-data.thelook_ecommerce`"
DML_DDL = [
    ("delete", f"DELETE FROM {DS}.orders"),
    ("update", f"UPDATE {DS}.orders SET status = 'x'"),
    ("insert", f"INSERT INTO {DS}.orders (id) VALUES (1)"),
    ("drop", f"DROP TABLE {DS}.orders"),
    ("create", "CREATE TABLE t (id INT64)"),
    ("alter", f"ALTER TABLE {DS}.orders ADD COLUMN x INT64"),
    (
        "merge",
        (
            f"MERGE {DS}.orders t USING {DS}.order_items s ON t.id = s.order_id "
            "WHEN MATCHED THEN UPDATE SET status = 'x'"
        ),
    ),
    ("truncate", f"TRUNCATE TABLE {DS}.orders"),
]


@pytest.mark.parametrize("sql", [s for _, s in DML_DDL], ids=[i for i, _ in DML_DDL])
def test_validate_dml_ddl_rejected(sql: str) -> None:
    with pytest.raises(SqlValidationError):
        validate_read_only_sql(sql)


def test_validate_multi_statement_rejected() -> None:
    with pytest.raises(MultiStatementError):
        validate_read_only_sql("SELECT 1; DROP TABLE x")


@pytest.mark.parametrize(
    "sql",
    [
        pytest.param(f"SELECT * FROM {DS}.inventory_items", id="disallowed_only"),
        pytest.param(
            f"SELECT * FROM {DS}.orders o JOIN {DS}.inventory_items i ON o.id = i.order_id",
            id="mixed_allowed_and_disallowed",
        ),
        pytest.param("SELECT * FROM orders", id="unqualified"),
    ],
)
def test_validate_disallowed_table_rejected(sql: str) -> None:
    with pytest.raises(DisallowedTableError):
        validate_read_only_sql(sql)


@pytest.mark.parametrize("sql", ["", "   ", "\n\t"], ids=["empty", "whitespace", "newline"])
def test_validate_empty_rejected(sql: str) -> None:
    with pytest.raises(SqlValidationError):
        validate_read_only_sql(sql)


ACCEPT = [
    pytest.param(f"SELECT COUNT(*) FROM {DS}.orders", id="select"),
    pytest.param(
        f"SELECT id FROM {DS}.orders UNION ALL SELECT id FROM {DS}.users",
        id="union_all",
    ),
    pytest.param(
        f"WITH recent AS (SELECT * FROM {DS}.orders WHERE status = 'Complete') SELECT COUNT(*) FROM recent",
        id="cte",
    ),
    pytest.param(
        f"SELECT o.user_id FROM {DS}.orders o JOIN {DS}.order_items i ON o.id = i.order_id",
        id="join_two_allowed",
    ),
    pytest.param("SELECT 1;", id="trailing_semicolon"),
]


@pytest.mark.parametrize("sql", ACCEPT)
def test_validate_readonly_accepted(sql: str) -> None:
    statement = validate_read_only_sql(sql)
    assert isinstance(statement, exp.Expression)


@pytest.mark.parametrize(
    "sql",
    [
        pytest.param(f"SELECT email AS customer FROM {DS}.users", id="email_alias"),
        pytest.param(f"SELECT CONCAT(first_name, ' ', last_name) AS customer_name FROM {DS}.users", id="concat_name"),
        pytest.param(f"SELECT u.street_address AS address FROM {DS}.users u", id="address_alias"),
    ],
)
def test_validate_output_pii_projection_rejected(sql: str) -> None:
    with pytest.raises(SqlValidationError, match="do not output PII columns; use user_id"):
        validate_read_only_sql(sql)


def test_validate_geo_dimension_output_accepted() -> None:
    statement = validate_read_only_sql(f"SELECT country, COUNT(*) AS users FROM {DS}.users GROUP BY country")

    assert isinstance(statement, exp.Expression)
