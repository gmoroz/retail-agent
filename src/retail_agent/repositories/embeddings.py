"""OpenRouter ``baai/bge-m3`` embeddings over the OpenAI-compatible client.

A single OpenRouter key serves chat models and embeddings (ADR-015). The OpenAI
client is used directly rather than ``langchain_openai.OpenAIEmbeddings`` so the
request mirrors the verified ``POST /api/v1/embeddings`` call exactly (no
tiktoken tokenization layer) and inherits the client's built-in retry/backoff
and timeout (Resilience) without an extra tenacity dependency.
"""

from functools import lru_cache

import openai

from retail_agent.config import get_settings
from retail_agent.const import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MAX_RETRIES,
    EMBEDDING_MODEL,
    EMBEDDING_REQUEST_TIMEOUT_SEC,
    OPENROUTER_BASE_URL,
)
from retail_agent.exceptions import EmbeddingError


@lru_cache(maxsize=1)
def get_client() -> openai.OpenAI:
    """Return the cached OpenAI client pointed at the OpenRouter endpoint."""

    settings = get_settings()
    return openai.OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=settings.openrouter_api_key.get_secret_value(),
        max_retries=EMBEDDING_MAX_RETRIES,
        timeout=EMBEDDING_REQUEST_TIMEOUT_SEC,
    )


def _embed(texts: list[str]) -> list[list[float]]:
    client = get_client()
    try:
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    except openai.APIError as exc:
        raise EmbeddingError(f"OpenRouter embeddings request failed: {exc}") from exc

    vectors = [item.embedding for item in response.data]
    for vector in vectors:
        if len(vector) != EMBEDDING_DIMENSION:
            raise EmbeddingError(f"expected {EMBEDDING_DIMENSION}-dim vector, got {len(vector)}")
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a single query string; raises :class:`EmbeddingError` on failure."""

    return _embed([text])[0]


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of documents, preserving input order."""

    if not texts:
        return []
    return _embed(texts)
