"""Unit tests for the interactive CLI loop."""

from collections.abc import Iterator

import pytest

import retail_agent.cli as cli


class GraphDouble:
    """Minimal graph double recording questions and thread ids."""

    def __init__(self, states: list[dict[str, object]] | None = None, failure: BaseException | None = None) -> None:
        self._states: Iterator[dict[str, object]] = iter(states or [])
        self._failure = failure
        self.questions: list[str] = []
        self.thread_ids: list[str] = []

    def invoke(self, agent_input: dict[str, object], config: dict[str, dict[str, str]]) -> dict[str, object]:
        self.questions.append(str(agent_input["question"]))
        self.thread_ids.append(config["configurable"]["thread_id"])
        if self._failure is not None:
            raise self._failure
        return next(self._states)


def _install_cli_doubles(
    monkeypatch: pytest.MonkeyPatch,
    graph: GraphDouble,
    commands: list[str],
) -> None:
    command_iter = iter(commands)

    def read_input(_prompt: str) -> str:
        return next(command_iter)

    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(cli, "build_graph", lambda: graph)
    monkeypatch.setattr("builtins.input", read_input)


def test_cli_prints_report_when_graph_returns_scrubbed_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    graph = GraphDouble(states=[{"outcome": "ok", "scrubbed_report": "Revenue was $42."}])
    _install_cli_doubles(monkeypatch, graph, ["How much revenue?", "/exit"])

    cli.main()

    stdout = capsys.readouterr().out
    assert "Revenue was $42." in stdout
    assert graph.questions == ["How much revenue?"]


def test_cli_prints_neutral_error_when_graph_raises_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    graph = GraphDouble(failure=RuntimeError("provider timeout"))
    _install_cli_doubles(monkeypatch, graph, ["How much revenue?", "/exit"])

    cli.main()

    stdout = capsys.readouterr().out
    assert "I could not process that question." in stdout
    assert "Goodbye." in stdout
    assert graph.questions == ["How much revenue?"]


def test_cli_exits_cleanly_when_exit_command_is_entered(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    graph = GraphDouble()
    _install_cli_doubles(monkeypatch, graph, ["/exit"])

    cli.main()

    stdout = capsys.readouterr().out
    assert "Goodbye." in stdout
    assert graph.questions == []


def test_cli_exits_cleanly_when_input_reaches_eof(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    graph = GraphDouble()

    def raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(cli, "build_graph", lambda: graph)
    monkeypatch.setattr("builtins.input", raise_eof)

    cli.main()

    stdout = capsys.readouterr().out
    assert "Goodbye." in stdout
    assert graph.questions == []


def test_cli_changes_thread_id_when_new_command_is_entered(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    graph = GraphDouble(
        states=[
            {"outcome": "ok", "scrubbed_report": "First report."},
            {"outcome": "ok", "scrubbed_report": "Second report."},
        ]
    )
    _install_cli_doubles(monkeypatch, graph, ["First question", "/new", "Second question", "/exit"])

    cli.main()

    stdout = capsys.readouterr().out
    assert "Started a new dialog." in stdout
    assert graph.questions == ["First question", "Second question"]
    assert graph.thread_ids[0] != graph.thread_ids[1]
