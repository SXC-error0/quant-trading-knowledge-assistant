from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str | bool]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "embedding_configuration_ready": settings.embedding_configuration_ready(),
        "llm_configuration_ready": settings.llm_configuration_ready(),
        "model_configuration_ready": settings.model_configuration_ready(),
    }
