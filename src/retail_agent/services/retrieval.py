"""Golden-bucket retrieval orchestration for SQL few-shot examples."""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from retail_agent.agent.state import GoldenTrioExample
from retail_agent.const import RETRIEVAL_TOP_K
from retail_agent.models import GoldenTrio
from retail_agent.repositories import embeddings, golden_bucket
from retail_agent.services.safety import mask_question


class RetrievalResult(BaseModel):
    """Masked user question plus retrieved few-shot examples."""

    model_config = ConfigDict(frozen=True)

    masked_question: str
    examples: list[GoldenTrioExample]


class GoldenRetrievalService(BaseModel):
    """Retrieve Golden Trios from a PII-masked user question."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    question_masker: Callable[[str], str] = mask_question
    query_embedder: Callable[[str], list[float]] = embeddings.embed_query
    golden_retriever: Callable[[list[float], int], list[GoldenTrio]] = golden_bucket.retrieve_similar
    top_k: int = RETRIEVAL_TOP_K

    def retrieve(self, question: str) -> RetrievalResult:
        """Return masked question text and top-k few-shot examples."""

        masked = self.question_masker(question)
        vector = self.query_embedder(masked)
        trios = self.golden_retriever(vector, self.top_k)
        return RetrievalResult(
            masked_question=masked,
            examples=[{"question": trio.question, "sql": trio.sql, "report": trio.report} for trio in trios],
        )
