from app.core.config import Settings
from app.models.knowledge import KnowledgeChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


class IngestionService:
    def __init__(self, embeddings: EmbeddingService, vector_store: VectorStore, settings: Settings) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._batch_size = settings.ingestion_batch_size

    async def import_chunks(self, chunks: list[KnowledgeChunk]) -> int:
        total = 0
        for i in range(0, len(chunks), self._batch_size):
            batch = chunks[i : i + self._batch_size]
            vectors = await self._embeddings.embed([c.content for c in batch])
            total += await self._vector_store.upsert(batch, vectors)
        return total
