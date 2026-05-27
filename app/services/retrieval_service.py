import re

from app.core.config import Settings
from app.models.knowledge import KnowledgeChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


def _terms(text: str) -> set[str]:
    ascii_terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower())
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return set(ascii_terms + chinese_terms)


class RetrievalService:
    """Vector recall with a lightweight keyword bonus; replace with a reranker later."""

    def __init__(
        self,
        settings: Settings,
        embeddings: EmbeddingService,
        vector_store: VectorStore,
    ) -> None:
        self._settings = settings
        self._embeddings = embeddings
        self._vector_store = vector_store

    async def retrieve(
        self,
        question: str,
        domains: list[str] | None,
        top_k: int,
    ) -> list[tuple[KnowledgeChunk, float]]:
        vector = (await self._embeddings.embed([question]))[0]
        candidates = await self._vector_store.search(
            vector,
            domains,
            max(top_k, self._settings.retrieval_candidate_k),
        )
        question_terms = _terms(question)
        rescored: list[tuple[KnowledgeChunk, float]] = []
        for chunk, vector_score in candidates:
            searchable = " ".join(
                [chunk.content, *chunk.keywords, chunk.chapter or "", chunk.section or ""]
            )
            overlaps = len(question_terms.intersection(_terms(searchable)))
            rescored.append((chunk, vector_score + min(overlaps * 0.03, 0.15)))
        return sorted(rescored, key=lambda item: item[1], reverse=True)[:top_k]
