"""Report assembly from an already-masked result DataFrame (ADR-010).

``run_sql`` masks rows before writing them to graph state, so the report model never
sees raw PII. The manager persona and the user-template live as module constants
(lightweight Agility: edit the prompt strings without touching the call site). The
report is returned verbatim; the email safety net (``scrub_report``) is applied by a
dedicated graph node, not duplicated here.
"""

import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

REPORT_SYSTEM_PROMPT = (
    "You are a retail analyst writing for a non-technical e-commerce manager. "
    "Turn the provided query result into a clear, concise insight: lead with the "
    "headline number, follow with one to three sentences of context (trends, "
    "comparisons, outliers), and avoid SQL jargon. If the result is empty, say so "
    "plainly instead of inventing figures. Use plain prose with at most a few short "
    "bullets. Never state numbers that are not present in the data. Never display "
    "customer PII such as email, names, street addresses, postal codes, latitude, "
    "longitude or user_geom. Do not describe missing customer PII as a query error "
    "or data problem, and do not suggest changing the query to select, add or "
    "request email, name, address, postal-code, coordinate or other raw PII columns. "
    "Identify customers with user_id only. If the user asks for customer PII, "
    "briefly state that customer personal data is not displayed; use aggregates or "
    "user_id identifiers instead, with no instructions for obtaining raw PII."
)

REPORT_USER_TEMPLATE = "Question:\n{question}\n\nQuery result:\n{table}\n\nWrite the report for the manager."
TRUNCATED_RESULT_TEMPLATE = "Only the first {shown_rows} of {total_rows} rows are shown due to the safety row cap."


def _format_table(df: pd.DataFrame) -> str:
    return df.to_string(index=False)


def build_report_messages(
    question: str,
    df: pd.DataFrame,
    *,
    truncated: bool = False,
    total_rows: int | None = None,
) -> list[BaseMessage]:
    """Build the system+user messages for the report model from ``df``."""

    table = _format_table(df)
    if truncated:
        table = f"{table}\n\n{_truncation_notice(len(df), total_rows)}"
    return [
        SystemMessage(content=REPORT_SYSTEM_PROMPT),
        HumanMessage(content=REPORT_USER_TEMPLATE.format(question=question, table=table)),
    ]


def generate_report(
    question: str,
    df: pd.DataFrame,
    chat_model: BaseChatModel,
    *,
    config: RunnableConfig | None = None,
    truncated: bool = False,
    total_rows: int | None = None,
) -> str:
    """Return the analytical report text for ``question`` over the masked ``df``."""

    response = chat_model.invoke(
        build_report_messages(question, df, truncated=truncated, total_rows=total_rows),
        config=config,
    )
    content = response.content
    report = content if isinstance(content, str) else str(content)
    if truncated:
        return f"{report}\n\n{_truncation_notice(len(df), total_rows)}"
    return report


def _truncation_notice(shown_rows: int, total_rows: int | None) -> str:
    return TRUNCATED_RESULT_TEMPLATE.format(total_rows=total_rows or shown_rows, shown_rows=shown_rows)
