"""
Retrieval endpoint.

POST /retrieve - Compute cosine similarity between source and target embeddings.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List
import torch
import time

from nexus_ecs_service.app.aws_logger import StructuredLogger

logger = StructuredLogger("nexus-ecs-service")
router = APIRouter()


class RetrieveRequest(BaseModel):
    """Request model for similarity search."""

    source_embedding: List[float] = Field(
        ...,
        description="Source control embedding (4096-dimensional)",
        min_length=1,
        max_length=10000
    )
    target_embeddings: List[List[float]] = Field(
        ...,
        description="Target control embeddings",
        min_length=1
    )
    top_k: int = Field(
        50,
        ge=1,
        le=1000,
        description="Number of top candidates to return"
    )


class CandidateMatch(BaseModel):
    """Model for a single candidate match."""

    control_id: str = Field(..., description="Index in target_embeddings array")
    similarity: float = Field(..., description="Cosine similarity score (0-1)")


class RetrieveResponse(BaseModel):
    """Response model for similarity search."""

    candidates: List[CandidateMatch] = Field(
        ..., description="Top-K candidates sorted by similarity"
    )


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_candidates(request: RetrieveRequest, http_request: Request):
    """
    Compute cosine similarity between source and target embeddings.

    This endpoint:
    1. Converts embeddings to PyTorch tensors
    2. Computes cosine similarity (dot product of normalized vectors)
    3. Finds top-K highest similarity scores
    4. Returns sorted candidates

    **Performance:**
    - 1,000 targets: <50ms
    - 10,000 targets: <200ms

    **Note:** Embeddings must be pre-normalized (use /embed endpoint).
    """
    start_time = time.time()
    request_id = getattr(http_request.state, 'request_id', 'unknown')

    try:
        num_targets = len(request.target_embeddings)

        logger.info(
            "Retrieve request received",
            num_targets=num_targets,
            top_k=request.top_k,
            source_dim=len(request.source_embedding),
            request_id=request_id
        )

        # Validate embedding dimensions
        source_dim = len(request.source_embedding)
        for idx, target_emb in enumerate(request.target_embeddings):
            if len(target_emb) != source_dim:
                raise ValueError(
                    f"Dimension mismatch at index {idx}: "
                    f"source has {source_dim}, target has {len(target_emb)}"
                )

        # Convert to tensors
        source_tensor = torch.tensor(
            request.source_embedding, dtype=torch.float32
        ).unsqueeze(0)
        target_tensor = torch.tensor(
            request.target_embeddings, dtype=torch.float32
        )

        # Compute cosine similarities
        similarities = torch.mm(source_tensor, target_tensor.T).squeeze()

        # Handle single target case
        if similarities.dim() == 0:
            similarities = similarities.unsqueeze(0)

        # Get top-K
        top_k_actual = min(request.top_k, len(similarities))
        top_scores, top_indices = torch.topk(similarities, top_k_actual)

        # Format response
        candidates = [
            CandidateMatch(
                control_id=str(idx.item()),
                similarity=float(score.item())
            )
            for idx, score in zip(top_indices, top_scores)
        ]

        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Retrieve request completed",
            num_targets=num_targets,
            top_k=top_k_actual,
            execution_time_ms=execution_time_ms,
            avg_similarity=float(top_scores.mean().item()) if len(top_scores) > 0 else 0,
            request_id=request_id
        )

        return RetrieveResponse(candidates=candidates)

    except ValueError as e:
        logger.error(
            "Validation error in retrieve",
            error_message=str(e),
            request_id=request_id
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "Retrieve request failed",
            num_targets=len(request.target_embeddings),
            error_type=type(e).__name__,
            error_message=str(e),
            execution_time_ms=execution_time_ms,
            request_id=request_id
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute similarities: {str(e)}"
        )
