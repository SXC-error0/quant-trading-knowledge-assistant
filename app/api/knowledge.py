from fastapi import APIRouter, HTTPException, Request, status

from app.models.knowledge import ImportChunksRequest, ImportChunksResponse

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/import", response_model=ImportChunksResponse)
async def import_chunks(payload: ImportChunksRequest, request: Request) -> ImportChunksResponse:
    settings = request.app.state.settings
    if not settings.embedding_configuration_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding configuration is required before importing chunks.",
        )
    count = await request.app.state.ingestion_service.import_chunks(payload.chunks)
    return ImportChunksResponse(imported_count=count, collection=settings.qdrant_collection)
