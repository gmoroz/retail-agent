"""Shared pytest fixtures and the integration-test gate.

Network/DB tests are marked ``@pytest.mark.integration`` and skipped unless the
``RUN_INTEGRATION=1`` environment variable is set, so ``make test`` stays green
without infrastructure.
"""

import os

import pytest

from retail_agent.config import get_settings


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if os.getenv("RUN_INTEGRATION"):
        return
    skip = pytest.mark.skip(reason="set RUN_INTEGRATION=1 to run integration tests")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> "object":
    """Provide a Settings instance backed by dummy env vars and refresh the cache."""

    monkeypatch.setenv("LLM_BASE_URL", "http://gateway.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "dummy-llm-key")
    monkeypatch.setenv("LLM_MODEL", "dummy-model")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-dummy")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "dummy-project")
    monkeypatch.setenv("DB_URI", "postgresql://u:p@localhost:5432/db")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()
