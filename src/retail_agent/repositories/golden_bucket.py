"""Golden-bucket access: pgvector few-shot Trios over a sync SQLAlchemy session.

The engine is built once from :attr:`Settings.sqlalchemy_url` (the derived
``postgresql+psycopg://`` form, ADR-021) and cached. ``ingest_trios`` embeds each
question via OpenRouter and bulk-inserts the rows; ``retrieve_similar`` returns
the ``top_k`` nearest Trios by cosine distance for few-shot injection
(Hybrid Intelligence).
"""

from collections.abc import Sequence
from functools import lru_cache

from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from retail_agent.config import get_settings
from retail_agent.exceptions import GoldenBucketError
from retail_agent.models import GoldenTrio
from retail_agent.repositories import embeddings


class GoldenTrioSeed(BaseModel):
    """Text-only Golden Trio; the embedding is computed on ingest."""

    model_config = ConfigDict(frozen=True)

    question: str
    sql: str
    report: str


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the cached SQLAlchemy engine for the Golden-bucket database."""

    return create_engine(get_settings().sqlalchemy_url, pool_pre_ping=True)


def ingest_trios(trios: Sequence[GoldenTrioSeed]) -> int:
    """Embed each question and bulk-insert the Trios; returns the count inserted.

    May raise :class:`retail_agent.exceptions.EmbeddingError` from the embedding
    call or :class:`GoldenBucketError` on a database failure.
    """

    questions = [trio.question for trio in trios]
    vectors = embeddings.embed_documents(questions)
    rows = [
        GoldenTrio(question=trio.question, sql=trio.sql, report=trio.report, embedding=vector)
        for trio, vector in zip(trios, vectors, strict=True)
    ]
    try:
        with Session(get_engine()) as session:
            session.add_all(rows)
            session.commit()
    except SQLAlchemyError as exc:
        raise GoldenBucketError(f"golden-bucket ingest failed: {exc}") from exc
    return len(rows)


def retrieve_similar(question_embedding: list[float], top_k: int) -> list[GoldenTrio]:
    """Return the ``top_k`` Trios nearest to ``question_embedding`` by cosine distance."""

    try:
        with Session(get_engine()) as session:
            stmt = select(GoldenTrio).order_by(GoldenTrio.embedding.cosine_distance(question_embedding)).limit(top_k)
            return list(session.scalars(stmt))
    except SQLAlchemyError as exc:
        raise GoldenBucketError(f"golden-bucket retrieve failed: {exc}") from exc
