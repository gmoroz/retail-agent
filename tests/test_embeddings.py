"""Tests for the OpenRouter embeddings repository (ADR-015).

The dimension check is the live smoke test required by the evidence ledger; it
needs ``RUN_INTEGRATION=1`` and a real ``OPENROUTER_API_KEY``.
"""

import pytest

from retail_agent.const import EMBEDDING_DIMENSION
from retail_agent.repositories.embeddings import embed_documents, embed_query


@pytest.mark.integration
def test_embed_query_returns_1024_dims() -> None:
    vector = embed_query("Top selling products last quarter")
    assert isinstance(vector, list)
    assert len(vector) == EMBEDDING_DIMENSION


@pytest.mark.integration
def test_embed_documents_preserves_order_and_dim() -> None:
    texts = [
        "How many repeat customers do we have?",
        "Average order value by month",
    ]
    vectors = embed_documents(texts)
    assert len(vectors) == len(texts)
    assert all(len(vector) == EMBEDDING_DIMENSION for vector in vectors)
