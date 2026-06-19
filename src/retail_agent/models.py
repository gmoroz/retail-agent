"""SQLAlchemy ORM models.

``Base.metadata`` is the Alembic migration target: ``alembic/env.py`` imports it
and autogenerate diff against it.
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from retail_agent.const import EMBEDDING_DIMENSION


class Base(DeclarativeBase):
    """Declarative base; its ``metadata`` drives Alembic autogenerate."""


class GoldenTrio(Base):
    """Few-shot example stored in the Golden bucket.

    A (question, SQL, report) triple with its OpenRouter ``baai/bge-m3`` embedding.
    Retrieved by cosine similarity over ``embedding`` to inject similar triples as
    few-shot context (Hybrid Intelligence).
    """

    __tablename__ = "golden_trios"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    report: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
