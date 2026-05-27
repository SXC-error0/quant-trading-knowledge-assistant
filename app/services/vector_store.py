from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from app.core.config import Settings
from app.models.knowledge import KnowledgeChunk


class VectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )

    async def ensure_collection(self) -> None:
        exists = await self._client.collection_exists(self._settings.qdrant_collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._settings.qdrant_collection,
                vectors_config=models.VectorParams(
                    size=self._settings.embedding_dimensions,
                    distance=models.Distance.COSINE,
                ),
            )

    async def upsert(self, chunks: list[KnowledgeChunk], vectors: list[list[float]]) -> int:
        await self.ensure_collection()
        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, chunk.chunk_id)),
                vector=vector,
                payload=chunk.model_dump(),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        await self._client.upsert(
            collection_name=self._settings.qdrant_collection,
            points=points,
            wait=True,
        )
        return len(points)

    async def search(
        self,
        query_vector: list[float],
        domains: list[str] | None,
        limit: int,
    ) -> list[tuple[KnowledgeChunk, float]]:
        await self.ensure_collection()
        query_filter = None
        if domains:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="knowledge_domain",
                        match=models.MatchAny(any=domains),
                    )
                ]
            )
        result = await self._client.query_points(
            collection_name=self._settings.qdrant_collection,
            query=query_vector,
            query_filter=query_filter,
            with_payload=True,
            limit=limit,
        )
        matches: list[tuple[KnowledgeChunk, float]] = []
        for point in result.points:
            if point.payload:
                matches.append((KnowledgeChunk.model_validate(point.payload), float(point.score)))
        return matches
