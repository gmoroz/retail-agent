"""String enums for graph outcomes and routing targets."""

from enum import StrEnum


class AgentOutcome(StrEnum):
    """Terminal outcome values stored in graph state and traces."""

    OK = "ok"
    BLOCKED = "blocked"
    NO_DATA = "no_data"
    COST_EXCEEDED = "cost_exceeded"
    FAILED = "failed"


class NodeRoute(StrEnum):
    """Conditional-edge targets used by the LangGraph workflow."""

    REFUSE = "refuse"
    FAILURE_RESPONSE = "failure_response"
    SCHEMA_REPORT = "schema_report"
    RETRIEVE_GOLDEN = "retrieve_golden"
    VALIDATE_SQL = "validate_sql"
    RUN_SQL = "run_sql"
    SELF_CORRECT = "self_correct"
    COST_REFUSAL = "cost_refusal"
    NO_DATA_REPORT = "no_data_report"
    GENERATE_REPORT = "generate_report"
    SCRUB_REPORT = "scrub_report"
