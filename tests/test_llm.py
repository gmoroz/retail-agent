"""Unit tests for the generic OpenAI-compatible chat model factory.

The factory is exercised without a network call: building a ``ChatOpenAI`` only wires
config into the client. The dev/generic path (``LLM_*``) must NOT request usage
inclusion (the dev gateway may not honour it), while OpenRouter paths (A/B slug and
judge) must pass ``extra_body={"usage": {"include": True}}`` so the observability
callback can read the charged cost (PR-006).
"""

import pytest
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from retail_agent.config import Settings
from retail_agent.const import JUDGE_MODEL, OPENROUTER_BASE_URL
from retail_agent.services.llm import build_chat_model

AB_SLUG = "deepseek/deepseek-v4-flash"


def test_build_chat_model_generic_uses_dev_endpoint(settings: object) -> None:
    model = build_chat_model()

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "http://gateway.example/v1"
    assert model.model_name == "dummy-model"
    assert model.max_retries == 3
    assert model.extra_body is None


def test_build_chat_model_ab_slug_uses_openrouter(settings: object) -> None:
    model = build_chat_model(model=AB_SLUG)

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == OPENROUTER_BASE_URL
    assert model.model_name == AB_SLUG
    assert model.extra_body == {"usage": {"include": True}}


def test_build_chat_model_judge_uses_judge_slug(settings: object) -> None:
    model = build_chat_model(for_judge=True)

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == OPENROUTER_BASE_URL
    assert model.model_name == JUDGE_MODEL
    assert model.extra_body == {"usage": {"include": True}}


def test_build_chat_model_judge_wins_over_model(settings: object) -> None:
    model = build_chat_model(model=AB_SLUG, for_judge=True)

    assert model.model_name == JUDGE_MODEL


@pytest.mark.integration
def test_openrouter_chat_returns_cost_in_usage() -> None:
    settings = Settings()

    model = build_chat_model(model=AB_SLUG, settings_provider=lambda: settings)
    response = model.invoke([HumanMessage(content="Reply with exactly one word: hello")])

    token_usage = response.response_metadata.get("token_usage", {})
    assert "cost" in token_usage
    assert token_usage["cost"] >= 0
    assert response.usage_metadata is not None
    assert response.usage_metadata["total_tokens"] > 0
