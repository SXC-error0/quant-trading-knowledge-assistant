from pydantic import BaseModel, Field

from app.models.knowledge import KnowledgeDomain
from app.models.signal import SignalContext


class ConversationTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    knowledge_domains: list[KnowledgeDomain] | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    signal_context: SignalContext | None = None
    history: list[ConversationTurn] = Field(
        default_factory=list,
        max_length=10,
        description="Up to 10 prior turns for multi-turn context.",
    )


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
