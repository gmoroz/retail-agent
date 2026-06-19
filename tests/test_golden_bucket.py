"""Integration tests for the Golden-bucket repository.

Require ``RUN_INTEGRATION=1``, a live Postgres (``make db-up && make db-migrate``)
and a real ``OPENROUTER_API_KEY`` (the embed step calls OpenRouter).
"""

import pytest

from retail_agent.repositories.embeddings import embed_query
from retail_agent.repositories.golden_bucket import (
    GoldenTrioSeed,
    ingest_trios,
    retrieve_similar,
)
from retail_agent.services.sql_validation import validate_read_only_sql


@pytest.mark.integration
def test_ingest_then_retrieve_returns_seed_first() -> None:
    seed = GoldenTrioSeed(
        question="Total orders by status",
        sql="SELECT status, COUNT(*) AS n FROM `bigquery-public-data.thelook_ecommerce`.orders GROUP BY status",
        report="Order counts grouped by status.",
    )
    count = ingest_trios([seed])
    assert count == 1

    validate_read_only_sql(seed.sql)

    nearest = retrieve_similar(embed_query(seed.question), top_k=1)
    assert nearest, "retrieve_similar should return at least one Trio"
    assert nearest[0].sql == seed.sql
