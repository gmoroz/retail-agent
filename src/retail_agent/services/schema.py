"""Schema metadata loading for graph prompts and schema questions."""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from retail_agent.repositories import bigquery


def format_schema_context(schema: dict[str, list[bigquery.ColumnSchema]]) -> str:
    """Render allowlist-table schema into compact prompt text."""

    lines: list[str] = []
    for table_name, columns in sorted(schema.items()):
        rendered_columns = ", ".join(f"{column.name} {column.data_type}" for column in columns)
        lines.append(f"- `{table_name}`: {rendered_columns}")
    return "\n".join(lines)


class SchemaService(BaseModel):
    """Load allowlist BigQuery schema and render it for the agent."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    schema_loader: Callable[[], dict[str, list[bigquery.ColumnSchema]]] = bigquery.introspect_schema

    def load_context(self) -> str:
        """Return the formatted allowlist schema context."""

        return format_schema_context(self.schema_loader())
