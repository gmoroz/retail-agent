"""Single generic OpenAI-compatible chat model factory (ADR-016, ADR-017).

One provider path serves the A/B agent models, the judge and dev runs: a
``ChatOpenAI`` built through ``init_chat_model(model_provider="openai")`` from
env-driven base_url/key/model. A/B slugs and the judge run against OpenRouter
(OpenRouter base_url + key + an explicit slug from ``const``); dev runs use
``LLM_BASE_URL``/``LLM_API_KEY``/``LLM_MODEL`` unchanged.

PR-006: OpenRouter calls carry ``extra_body={"usage": {"include": True}}`` so the
response includes the charged ``cost``; the observability callback reads it back from
``response_metadata["token_usage"]["cost"]``. ``extra_body`` (not ``model_kwargs``) is
required because ``model_kwargs`` are forwarded as top-level arguments to the OpenAI
client's ``completions.create``, which rejects an unknown ``usage`` argument; OpenRouter
expects ``usage`` inside the request body. Built-in ``max_retries`` and ``timeout``
handle transient failures (Resilience). The factory intentionally does not memoize: the
A/B sweep builds one model per slug and per-run isolation matters more than the one-time
client-construction cost.
"""

from collections.abc import Callable
from typing import cast

from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

from retail_agent.config import Settings, get_settings
from retail_agent.const import JUDGE_MODEL, LLM_MAX_RETRIES, LLM_REQUEST_TIMEOUT_SEC, OPENROUTER_BASE_URL

OR_USAGE_BODY = {"usage": {"include": True}}


def build_chat_model(
    model: str | None = None,
    *,
    for_judge: bool = False,
    settings_provider: Callable[[], Settings] = get_settings,
) -> ChatOpenAI:
    """Build a generic OpenAI-compatible chat model.

    With no arguments the dev/generic endpoint (``LLM_*``) is used. ``model`` selects
    an A/B slug over OpenRouter; ``for_judge`` selects the judge slug. ``for_judge``
    wins when both are set. OpenRouter calls request usage inclusion so the observability
    callback can read the charged cost (PR-006).
    """

    settings = settings_provider()
    if for_judge or model is not None:
        slug = JUDGE_MODEL if for_judge else model
        if slug is None:
            raise ValueError("model slug is required when for_judge is False")
        return cast(
            ChatOpenAI,
            init_chat_model(
                model=slug,
                model_provider="openai",
                base_url=OPENROUTER_BASE_URL,
                api_key=settings.openrouter_api_key.get_secret_value(),
                extra_body=OR_USAGE_BODY,
                max_retries=LLM_MAX_RETRIES,
                timeout=LLM_REQUEST_TIMEOUT_SEC,
            ),
        )
    return cast(
        ChatOpenAI,
        init_chat_model(
            model=settings.llm_model,
            model_provider="openai",
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            max_retries=LLM_MAX_RETRIES,
            timeout=LLM_REQUEST_TIMEOUT_SEC,
        ),
    )
