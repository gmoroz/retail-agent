"""Read-only SQL validation via the sqlglot AST (ADR-009, ADR-018).

Pure logic, no I/O: the validator never touches BigQuery; dry-run byte estimation
lives in :mod:`retail_agent.repositories.bigquery`. The contract enforced here is
the single combined rule from plan review (PR-001/002/008):

1. exactly one statement -- ``sqlglot.parse`` (not ``parse_one``) so a trailing
   ``; DROP TABLE`` is not silently dropped (PR-001);
2. read-only deny-list -- reject any DML/DDL node in the tree rather than
   allow-listing ``exp.Select`` alone, so top-level ``UNION``/``UNION ALL``/CTE
   pass (PR-008);
3. table subset -- every referenced table must be in :data:`ALLOWED_TABLES`;
   a mixed allowed-plus-external query is rejected, not merely "contains one
   allowed" (PR-002).
"""

from typing import cast

import sqlglot
from sqlglot import exp

from retail_agent.const import ALLOWED_TABLES, PII_COLUMN_NAMES, READONLY_SQL_DENYLIST
from retail_agent.exceptions import (
    DisallowedTableError,
    MultiStatementError,
    SqlValidationError,
)

READONLY_DENY_NODES: tuple[type[exp.Expression], ...] = tuple(getattr(exp, name) for name in READONLY_SQL_DENYLIST)


def _table_key(table: exp.Table) -> str:
    if table.db:
        return f"{table.db}.{table.name}"
    return table.name


def _referenced_tables(statement: exp.Expression) -> set[str]:
    cte_aliases = {cte.alias for cte in statement.find_all(exp.CTE)}
    return {_table_key(table) for table in statement.find_all(exp.Table) if table.name not in cte_aliases}


def _output_selects(statement: exp.Expression) -> list[exp.Select]:
    if isinstance(statement, exp.Select):
        return [statement]
    if isinstance(statement, exp.Subquery):
        return _output_selects(statement.this)
    if isinstance(statement, exp.Union):
        return _output_selects(cast(exp.Expression, statement.left)) + _output_selects(
            cast(exp.Expression, statement.right)
        )
    return list(statement.find_all(exp.Select))


def _output_pii_columns(statement: exp.Expression) -> set[str]:
    pii_columns: set[str] = set()
    for select in _output_selects(statement):
        for projection in select.expressions:
            pii_columns.update(
                column.name for column in projection.find_all(exp.Column) if column.name in PII_COLUMN_NAMES
            )
    return pii_columns


def validate_read_only_sql(sql: str) -> exp.Expression:
    """Validate ``sql`` as a single read-only statement over the allowlist.

    Returns the parsed statement on success (render with ``.sql(dialect="bigquery")``
    for the dry-run/execution path). Raises :class:`SqlValidationError` on a parse
    failure or empty query, :class:`MultiStatementError` when more than one
    statement is present, or :class:`DisallowedTableError` when any referenced
    table is outside :data:`ALLOWED_TABLES`.
    """

    try:
        statements = sqlglot.parse(sql, dialect="bigquery")
    except sqlglot.errors.ParseError as exc:
        raise SqlValidationError(f"SQL failed to parse: {exc}") from exc

    if len(statements) != 1:
        raise MultiStatementError(f"expected exactly one statement, got {len(statements)}")

    statement = statements[0]
    if not isinstance(statement, exp.Expression):
        raise SqlValidationError("SQL is empty")

    deny_hit = statement.find(*READONLY_DENY_NODES)
    if deny_hit is not None:
        raise SqlValidationError(f"read-only deny-list hit: {type(deny_hit).__name__}")

    disallowed = _referenced_tables(statement) - ALLOWED_TABLES
    if disallowed:
        raise DisallowedTableError(f"tables outside the allowlist: {sorted(disallowed)}")

    pii_output = _output_pii_columns(statement)
    if pii_output:
        raise SqlValidationError(f"do not output PII columns; use user_id instead: {sorted(pii_output)}")

    return statement
