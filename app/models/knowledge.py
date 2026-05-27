from typing import Literal

from pydantic import BaseModel, Field

KnowledgeDomain = Literal["trading_books", "product_manual", "signal_rules"]


class KnowledgeChunk(BaseModel):
    chunk_id: str = Field(min_length=1, max_length=200)
    knowledge_domain: KnowledgeDomain
    document_title: str = Field(min_length=1, max_length=300)
    chapter: str | None = Field(default=None, max_length=300)
    section: str | None = Field(default=None, max_length=300)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    content: str = Field(min_length=10)
    keywords: list[str] = Field(default_factory=list)
    source_type: str = Field(default="document", max_length=50)
    copyright_status: str | None = Field(default=None, max_length=100)


class ImportChunksRequest(BaseModel):
    chunks: list[KnowledgeChunk] = Field(min_length=1, max_length=1000)


class ImportChunksResponse(BaseModel):
    imported_count: int
    collection: str
