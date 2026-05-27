from openai import AsyncOpenAI

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Create embeddings through an OpenAI-compatible endpoint.

        EMBEDDING_DIMENSIONS configures Qdrant vector size. Ensure it matches
        the actual output size of the selected embedding model.
        """
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
