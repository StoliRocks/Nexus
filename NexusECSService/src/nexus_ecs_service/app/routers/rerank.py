"""
Reranking endpoint.

POST /rerank - Rerank candidates using cross-encoder model.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List
import time

from nexus_ecs_service.app.services.reranker import RerankerService
from nexus_ecs_service.app.startup import MODELS
from nexus_ecs_service.app.aws_logger import StructuredLogger

logger = StructuredLogger("nexus-ecs-service")
router = APIRouter()


class CandidateInput(BaseModel):
    """Model for a candidate control."""

    control_id: str = Field(..., description="Control ID")
    text: str = Field(..., description="Control text")


class RerankRequest(BaseModel):
    """Request model for reranking."""

    source_text: str = Field(
        ...,
        description="Source control text",
        example="Ensure IAM users are managed through centralized identity provider"
    )
    candidates: List[CandidateInput] = Field(
        ...,
        description="Candidate controls to rerank",
        min_length=1
    )


class RankedCandidate(BaseModel):
    """Model for a ranked candidate."""

    control_id: str = Field(..., description="Control ID")
    score: float = Field(..., description="Cross-encoder score (0-1)")


class RerankResponse(BaseModel):
    """Response model for reranking."""

    rankings: List[RankedCandidate] = Field(
        ...,
        description="Ranked candidates sorted by score (descending)"
    )


@router.post("/rerank", response_model=RerankResponse)
async def rerank_candidates(request: RerankRequest, http_request: Request):
    """
    Rerank candidates using cross-encoder model.

    This endpoint:
    1. Creates (source, candidate) text pairs
    2. Scores each pair using ModernBERT cross-encoder
    3. Sorts by score descending
    4. Returns all ranked candidates

    **Performance:**
    - 50 candidates: 2-3 seconds
    - 100 candidates: 4-5 seconds
    - Batch size: 32 pairs per forward pass

    **Note:** For threshold filtering, apply on client side or pass threshold
    to Lambda orchestrator.
    """
    start_time = time.time()
    request_id = getattr(http_request.state, 'request_id', 'unknown')

    try:
        num_candidates = len(request.candidates)

        logger.info(
            "Rerank request received",
            num_candidates=num_candidates,
            source_text_length=len(request.source_text),
            request_id=request_id
        )

        reranker_service = RerankerService(
            model=MODELS['reranker']
        )

        candidates_dict = [
            {
                'control_id': c.control_id,
                'text': c.text
            }
            for c in request.candidates
        ]

        # Rerank (no threshold filtering - return all scores)
        rankings = await reranker_service.rerank_candidates(
            source_text=request.source_text,
            candidates=candidates_dict,
            threshold=0.0
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Rerank request completed",
            num_candidates=num_candidates,
            num_ranked=len(rankings),
            execution_time_ms=execution_time_ms,
            avg_time_per_pair_ms=execution_time_ms // num_candidates if num_candidates else 0,
            max_score=rankings[0]['score'] if rankings else 0,
            request_id=request_id
        )

        return RerankResponse(
            rankings=[
                RankedCandidate(
                    control_id=r['control_id'],
                    score=r['score']
                )
                for r in rankings
            ]
        )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "Rerank request failed",
            num_candidates=len(request.candidates),
            error_type=type(e).__name__,
            error_message=str(e),
            execution_time_ms=execution_time_ms,
            request_id=request_id
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to rerank candidates: {str(e)}"
        )
