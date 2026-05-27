import re

from rank_bm25 import BM25Okapi

from app.core.config import Settings
from app.models.knowledge import KnowledgeChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

_VECTOR_WEIGHT = 0.7
_BM25_WEIGHT = 0.3


def _tokenize(text: str) -> list[str]:
    ascii_terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower())
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return ascii_terms + chinese_terms


class RetrievalService:
    """Hybrid retrieval: vector recall + BM25 re-rank over candidates."""

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
        if not candidates:
            return []

        chunks = [chunk for chunk, _ in candidates]
        vector_scores = {chunk.chunk_id: score for chunk, score in candidates}

        corpus = [
            _tokenize(
                " ".join([c.content, *c.keywords, c.chapter or "", c.section or ""])
            )
            for c in chunks
        ]
        bm25 = BM25Okapi(corpus)
        raw_bm25 = bm25.get_scores(_tokenize(question))
        max_bm25 = float(raw_bm25.max())
        normalized_bm25 = raw_bm25 / max_bm25 if max_bm25 > 0 else raw_bm25

        rescored: list[tuple[KnowledgeChunk, float]] = [
            (chunk, _VECTOR_WEIGHT * vector_scores[chunk.chunk_id] + _BM25_WEIGHT * float(normalized_bm25[i]))
            for i, chunk in enumerate(chunks)
        ]
        return sorted(rescored, key=lambda item: item[1], reverse=True)[:top_k]
