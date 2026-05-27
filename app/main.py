from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import chat, health, knowledge
from app.core.config import get_settings
from app.services.answer_service import AnswerService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.vector_store import VectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    embeddings = EmbeddingService(settings)
    vector_store = VectorStore(settings)
    llm = LLMService(settings)
    retrieval = RetrievalService(settings, embeddings, vector_store)

    app.state.settings = settings
    app.state.ingestion_service = IngestionService(embeddings, vector_store, settings)
    app.state.answer_service = AnswerService(retrieval, llm)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="基于可引用知识片段的量化交易专业知识问答服务。",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(knowledge.router, prefix=settings.api_v1_prefix)
app.include_router(chat.router, prefix=settings.api_v1_prefix)
