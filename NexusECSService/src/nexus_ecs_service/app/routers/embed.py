"""
Embedding generation endpoint.

POST /embed - Generate vector embeddings for control text with caching.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List
import time

from nexus_ecs_service.app.services.embedder import EmbedderService
from nexus_ecs_service.app.services.embedding_cache import EmbeddingCacheService
from nexus_ecs_service.app.startup import MODELS
from nexus_ecs_service.app.aws_logger import StructuredLogger

logger = StructuredLogger("nexus-ecs-service")
router = APIRouter()


class EmbedRequest(BaseModel):
    """Request model for embedding generation."""

    control_id: str = Field(
        ...,
        description="Control ID for caching (e.g., 'IAM.21')",
        example="IAM.21"
    )
    text: str = Field(
        ...,
        description="Control text to embed",
        example="Ensure IAM users are managed through a centralized identity provider"
    )


class EmbedResponse(BaseModel):
    """Response model for embedding generation."""

    control_id: str = Field(..., description="Control ID")
    embedding: List[float] = Field(..., description="4096-dimensional embedding vector")
    cache_hit: bool = Field(..., description="Whether embedding was retrieved from cache")


@router.post("/embed", response_model=EmbedResponse)
async def generate_embedding(request: EmbedRequest, http_request: Request):
    """
    Generate embedding for control text.

    This endpoint:
    1. Checks if embedding is cached in DynamoDB
    2. If not cached, generates using Qwen bi-encoder model
    3. Stores new embedding in cache for future use
    4. Returns 4096-dimensional embedding vector

    **Performance:**
    - Cache hit: <10ms
    - Cache miss: 50-100ms (model inference)
    """
    start_time = time.time()
    request_id = getattr(http_request.state, 'request_id', 'unknown')

    try:
        logger.info(
            "Embed request received",
            control_id=request.control_id,
            text_length=len(request.text),
            request_id=request_id
        )

        embedder_service = EmbedderService(
            model=MODELS['retriever'],
            embedding_cache=EmbeddingCacheService()
        )

        result = await embedder_service.get_or_generate_embedding(
            control_id=request.control_id,
            text=request.text
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Embed request completed",
            control_id=request.control_id,
            cache_hit=result['cache_hit'],
            embedding_dim=len(result['embedding']),
            execution_time_ms=execution_time_ms,
            request_id=request_id
        )

        return EmbedResponse(
            control_id=request.control_id,
            embedding=result['embedding'],
            cache_hit=result['cache_hit']
        )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "Embed request failed",
            control_id=request.control_id,
            error_type=type(e).__name__,
            error_message=str(e),
            execution_time_ms=execution_time_ms,
            request_id=request_id
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embedding: {str(e)}"
        )
