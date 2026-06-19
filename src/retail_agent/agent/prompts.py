"""Prompt templates for SQL generation and self-correction."""

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from retail_agent.agent.state import GoldenTrioExample

SQL_SYSTEM_PROMPT = (
    "You generate BigQuery GoogleSQL for the public "
    "`bigquery-public-data.thelook_ecommerce` dataset. Return exactly one read-only "
    "SQL statement and no Markdown. Use only the allowed tables shown in the schema "
    "context. Prefer explicit aliases, aggregate carefully, and add a reasonable "
    "LIMIT for row-level outputs. Never write DDL, DML, scripts, temporary tables, "
    "or multiple statements. Do not output raw PII such as emails, names, street "
    "addresses, postal codes, latitude, longitude or user_geom; identify customers "
    "with user_id instead."
)

SQL_USER_TEMPLATE = """Question:
{question}

Schema:
{schema_context}

Few-shot examples:
{few_shot}
{feedback}
Return only the SQL statement."""

SELF_CORRECT_TEMPLATE = """

Previous SQL:
{sql}

The previous attempt failed with:
{error}

Revise the SQL while preserving the user's analytical intent."""

NO_EXAMPLES = "No similar examples were retrieved."


def format_few_shot_examples(examples: list[GoldenTrioExample]) -> str:
    """Render retrieved Golden Trios for SQL few-shot prompting."""

    if not examples:
        return NO_EXAMPLES
    blocks = []
    for index, example in enumerate(examples, start=1):
        blocks.append(
            "\n".join(
                (
                    f"Example {index}:",
                    f"Question: {example['question']}",
                    f"SQL: {example['sql']}",
                    f"Report: {example['report']}",
                )
            )
        )
    return "\n\n".join(blocks)


def build_sql_messages(
    *,
    question: str,
    schema_context: str,
    few_shot: list[GoldenTrioExample],
    previous_sql: str | None = None,
    error: str | None = None,
) -> list[BaseMessage]:
    """Build the SQL-generation prompt, optionally with self-correction feedback."""

    feedback = ""
    if previous_sql and error:
        feedback = SELF_CORRECT_TEMPLATE.format(sql=previous_sql, error=error)
    return [
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        HumanMessage(
            content=SQL_USER_TEMPLATE.format(
                question=question,
                schema_context=schema_context,
                few_shot=format_few_shot_examples(few_shot),
                feedback=feedback,
            )
        ),
    ]
