"""Interactive command-line interface for the retail-analysis agent."""

import logging
from collections.abc import Mapping
from typing import cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from retail_agent.agent.graph import build_graph, close_graph_resources
from retail_agent.agent.state import AgentState
from retail_agent.exceptions import RetailAgentError
from retail_agent.services.observability import configure_logging

logger = logging.getLogger(__name__)

PROMPT = "retail> "
WELCOME = "Retail analytics agent. Type a question, /new for a new dialog, or /exit to quit."
GOODBYE = "Goodbye."
NEW_DIALOG = "Started a new dialog."
NEUTRAL_ERROR = "I could not process that question. Please try again with a narrower request."
OUTCOME_MESSAGES: Mapping[str, str] = {
    "blocked": "I cannot help with that request. Please ask a retail analytics question.",
    "no_data": "No matching data was returned for this question.",
    "cost_exceeded": "The query is too large to run within the configured cost limit.",
    "failed": NEUTRAL_ERROR,
}


def _new_thread_id() -> str:
    return uuid4().hex


def _config(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id}}


def _reply_from_state(agent_state: Mapping[str, object]) -> str:
    report = agent_state.get("scrubbed_report")
    if isinstance(report, str) and report:
        return report
    outcome = agent_state.get("outcome")
    if isinstance(outcome, str):
        return OUTCOME_MESSAGES.get(outcome, NEUTRAL_ERROR)
    return NEUTRAL_ERROR


def _invoke_graph(
    graph: CompiledStateGraph[AgentState, None, AgentState, AgentState],
    question: str,
    thread_id: str,
) -> Mapping[str, object]:
    agent_input: AgentState = {"question": question}
    return cast(Mapping[str, object], graph.invoke(agent_input, config=_config(thread_id)))


def main() -> None:
    """Run the interactive retail-agent chat loop."""

    configure_logging()
    try:
        graph = build_graph()
        thread_id = _new_thread_id()

        print(WELCOME)
        while True:
            try:
                question = input(PROMPT).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                print(GOODBYE)
                return

            if not question:
                continue
            if question == "/exit":
                print(GOODBYE)
                return
            if question == "/new":
                thread_id = _new_thread_id()
                print(NEW_DIALOG)
                continue

            try:
                agent_state = _invoke_graph(graph, question, thread_id)
            except KeyboardInterrupt:
                print()
                print(GOODBYE)
                return
            except RetailAgentError:
                logger.exception("agent invocation failed")
                print(NEUTRAL_ERROR)
            except (RuntimeError, TimeoutError, ValueError, TypeError, KeyError):
                logger.exception("unexpected agent invocation failed")
                print(NEUTRAL_ERROR)
            else:
                print(_reply_from_state(agent_state))
    finally:
        close_graph_resources()
