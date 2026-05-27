from fastapi import APIRouter, HTTPException, Request, status

from app.core.safety import assess_question
from app.models.chat import AskRequest, AskResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, request: Request) -> AskResponse:
    settings = request.app.state.settings
    risk = assess_question(payload.question)
    if not risk.blocked and not settings.model_configuration_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model configuration is required before knowledge questions can be answered.",
        )
    domains = (
        [str(domain) for domain in payload.knowledge_domains]
        if payload.knowledge_domains
        else None
    )
    return await request.app.state.answer_service.ask(payload.question, domains, payload.top_k)
