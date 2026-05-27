import json

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.safety import assess_question
from app.models.chat import AskRequest, AskResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def _resolve_domains(payload: AskRequest) -> list[str] | None:
    return [str(d) for d in payload.knowledge_domains] if payload.knowledge_domains else None


def _check_model_ready(request: Request, payload: AskRequest) -> None:
    settings = request.app.state.settings
    risk = assess_question(payload.question, has_signal_context=payload.signal_context is not None)
    if not risk.blocked and not settings.model_configuration_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model configuration is required before knowledge questions can be answered.",
        )


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, request: Request) -> AskResponse:
    _check_model_ready(request, payload)
    return await request.app.state.answer_service.ask(
        payload.question,
        _resolve_domains(payload),
        payload.top_k,
        signal=payload.signal_context,
        history=payload.history or None,
    )


@router.post("/ask/stream")
async def ask_stream(payload: AskRequest, request: Request) -> StreamingResponse:
    """Server-Sent Events stream.

    Event types:
    - ``{"type": "token",   "content": "..."}``          incremental LLM text
    - ``{"type": "sources", "sources": [...]}``           citations after generation
    - ``{"type": "done",    "risk_notice": "..."}``       end sentinel
    - ``{"type": "answer",  "content": "...", "boundary_triggered": true}``  guarded response
    """
    _check_model_ready(request, payload)

    async def _generate():
        async for event in request.app.state.answer_service.ask_stream(
            payload.question,
            _resolve_domains(payload),
            payload.top_k,
            signal=payload.signal_context,
            history=payload.history or None,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")
