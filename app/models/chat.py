from pydantic import BaseModel, Field

from app.models.knowledge import KnowledgeDomain


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    knowledge_domains: list[KnowledgeDomain] | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class SourceReference(BaseModel):
    chunk_id: str
    knowledge_domain: KnowledgeDomain
    document_title: str
    chapter: str | None = None
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    score: float | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    risk_notice: str
    boundary_triggered: bool = False
