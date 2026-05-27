from app.models.knowledge import KnowledgeChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


class IngestionService:
    def __init__(self, embeddings: EmbeddingService, vector_store: VectorStore) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store

    async def import_chunks(self, chunks: list[KnowledgeChunk]) -> int:
        vectors = await self._embeddings.embed([chunk.content for chunk in chunks])
        return await self._vector_store.upsert(chunks, vectors)
