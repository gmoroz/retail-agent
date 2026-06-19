"""Read-only SQL validation via the sqlglot AST (ADR-009, ADR-018).

Pure logic, no I/O: the validator never touches BigQuery; dry-run byte estimation
lives in :mod:`retail_agent.repositories.bigquery`. The contract enforced here is
the single combined rule from plan review (PR-001/002/008) plus the safety-bypass
hardening:

1. exactly one statement -- ``sqlglot.parse`` (not ``parse_one``) so a trailing
   ``; DROP TABLE`` is not silently dropped (PR-001);
2. top-level read-only allow-list -- only ``SELECT`` and ``UNION`` statements may
   proceed;
3. read-only deny-list -- reject any DML/DDL node in the tree as defense in depth;
4. table subset -- every referenced table must be in :data:`ALLOWED_TABLES`;
   a mixed allowed-plus-external query is rejected, not merely "contains one
   allowed" (PR-002).
"""

from typing import cast

import sqlglot
from sqlglot import exp

from retail_agent.const import (
    ALLOWED_TABLES,
    PII_COLUMN_NAMES,
    PII_COLUMNS,
    READONLY_SQL_DENYLIST,
)
from retail_agent.exceptions import (
    DisallowedTableError,
    MultiStatementError,
    SqlValidationError,
)

READONLY_DENY_NODES: tuple[type[exp.Expression], ...] = tuple(getattr(exp, name) for name in READONLY_SQL_DENYLIST)
READONLY_TOP_NODES: tuple[type[exp.Expression], ...] = (exp.Select, exp.Union)


def _table_key(table: exp.Table) -> str:
    if table.catalog and table.db:
        return f"{table.catalog}.{table.db}.{table.name}"
    if table.db:
        return f"{table.db}.{table.name}"
    return table.name


def _is_cte_reference(table: exp.Table, cte_aliases: set[str]) -> bool:
    return not table.catalog and not table.db and table.name in cte_aliases


def _referenced_tables(statement: exp.Expression) -> set[str]:
    cte_aliases = {cte.alias for cte in statement.find_all(exp.CTE)}
    return {_table_key(table) for table in statement.find_all(exp.Table) if not _is_cte_reference(table, cte_aliases)}


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


def _pii_table_aliases(statement: exp.Expression) -> set[str]:
    cte_aliases = {cte.alias for cte in statement.find_all(exp.CTE)}
    return {
        table.alias_or_name
        for table in statement.find_all(exp.Table)
        if not _is_cte_reference(table, cte_aliases) and table.name in PII_COLUMNS
    }


def _output_whole_pii_row_references(statement: exp.Expression, pii_aliases: set[str]) -> set[str]:
    whole_row_references: set[str] = set()
    for select in _output_selects(statement):
        for projection in select.expressions:
            whole_row_references.update(
                column.name
                for column in projection.find_all(exp.Column)
                if not column.table and column.name in pii_aliases
            )
    return whole_row_references


def _is_readonly_top_statement(statement: exp.Expression) -> bool:
    if isinstance(statement, exp.Subquery):
        return _is_readonly_top_statement(statement.this)
    return isinstance(statement, READONLY_TOP_NODES)


def _projection_has_output_star(projection: exp.Expression) -> bool:
    if projection.is_star:
        return True
    if isinstance(projection, exp.Alias) and projection.this.is_star:
        return True
    return any(isinstance(column, exp.Column) and column.is_star for column in projection.find_all(exp.Column))


def _outputs_star(statement: exp.Expression) -> bool:
    return any(
        _projection_has_output_star(projection)
        for select in _output_selects(statement)
        for projection in select.expressions
    )


def _references_pii_table(referenced_tables: set[str]) -> bool:
    return any(table.rsplit(".", maxsplit=1)[-1] in PII_COLUMNS for table in referenced_tables)


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

    if not _is_readonly_top_statement(statement):
        raise SqlValidationError(f"only SELECT or UNION statements are allowed, got {type(statement).__name__}")

    deny_hit = statement.find(*READONLY_DENY_NODES)
    if deny_hit is not None:
        raise SqlValidationError(f"read-only deny-list hit: {type(deny_hit).__name__}")

    referenced_tables = _referenced_tables(statement)
    disallowed = referenced_tables - ALLOWED_TABLES
    if disallowed:
        raise DisallowedTableError(f"tables outside the allowlist: {sorted(disallowed)}")

    if _outputs_star(statement) and _references_pii_table(referenced_tables):
        raise SqlValidationError("do not SELECT * from PII-bearing tables; enumerate non-PII columns; use user_id")

    pii_output = _output_pii_columns(statement)
    if pii_output:
        raise SqlValidationError(f"do not output PII columns; use user_id instead: {sorted(pii_output)}")

    whole_pii_rows = _output_whole_pii_row_references(statement, _pii_table_aliases(statement))
    if whole_pii_rows:
        raise SqlValidationError(
            "do not output whole PII rows or structs; select explicit non-PII columns or user_id: "
            f"{sorted(whole_pii_rows)}"
        )

    return statement
