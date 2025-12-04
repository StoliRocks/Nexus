"""Reasoning API router - Mapping rationale generation."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nexus_strands_agent_service.app.services.reasoning_service import ReasoningService

logger = logging.getLogger(__name__)

router = APIRouter()


class MappingInput(BaseModel):
    """Input model for a single mapping."""

    target_control_id: str = Field(..., alias="targetControlId", description="Target control ID")
    target_framework: str = Field(..., alias="targetFramework", description="Target framework name")
    text: str = Field(default="", description="Target control text")
    similarity_score: float = Field(
        default=0.0, alias="similarityScore", description="Embedding similarity score"
    )
    rerank_score: float = Field(
        default=0.0, alias="rerankScore", description="Cross-encoder rerank score"
    )

    class Config:
        populate_by_name = True


class ReasoningRequest(BaseModel):
    """Request model for single mapping reasoning."""

    source_control_id: str = Field(
        ..., alias="sourceControlId", description="AWS control identifier"
    )
    source_text: str = Field(..., alias="sourceText", description="AWS control description")
    mapping: MappingInput = Field(..., description="Mapping to generate reasoning for")

    class Config:
        populate_by_name = True


class BatchReasoningRequest(BaseModel):
    """Request model for batch mapping reasoning."""

    source_control_id: str = Field(
        ..., alias="sourceControlId", description="AWS control identifier"
    )
    source_text: str = Field(..., alias="sourceText", description="AWS control description")
    mappings: List[MappingInput] = Field(
        ..., description="Mappings to generate reasoning for (max 20)"
    )

    class Config:
        populate_by_name = True


class ConsolidatedReasoningRequest(BaseModel):
    """Request model for consolidated reasoning (single API call for all mappings)."""

    source_control_id: str = Field(
        ..., alias="sourceControlId", description="AWS control identifier"
    )
    source_text: str = Field(..., alias="sourceText", description="AWS control description")
    mappings: List[MappingInput] = Field(
        ..., description="Mappings to generate consolidated reasoning for (max 10)"
    )

    class Config:
        populate_by_name = True


class ReasoningResponse(BaseModel):
    """Response model for single mapping reasoning."""

    source_control_id: str = Field(..., alias="sourceControlId")
    target_control_id: str = Field(..., alias="targetControlId")
    reasoning: str = Field(..., description="Human-readable rationale for the mapping")
    status: str = Field(..., description="Processing status (success/failed)")

    class Config:
        populate_by_name = True


class BatchReasoningResponse(BaseModel):
    """Response model for batch reasoning."""

    results: List[ReasoningResponse] = Field(..., description="Reasoning results")
    total: int = Field(..., description="Total mappings processed")
    successful: int = Field(..., description="Successfully processed count")
    failed: int = Field(..., description="Failed count")


class ConsolidatedReasoningResponse(BaseModel):
    """Response model for consolidated reasoning."""

    source_control_id: str = Field(..., alias="sourceControlId")
    consolidated_reasoning: str = Field(
        ..., alias="consolidatedReasoning", description="Consolidated reasoning for all mappings"
    )
    mapping_count: int = Field(..., alias="mappingCount", description="Number of mappings processed")
    status: str = Field(..., description="Processing status")

    class Config:
        populate_by_name = True


# Service instance (initialized on startup)
_reasoning_service: Optional[ReasoningService] = None


def get_reasoning_service() -> ReasoningService:
    """Get or create reasoning service instance."""
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService()
    return _reasoning_service


@router.post("/reason", response_model=ReasoningResponse)
async def generate_reasoning(request: ReasoningRequest) -> ReasoningResponse:
    """
    Generate human-readable rationale for a single control mapping.

    Explains why the source AWS control maps to the target framework control,
    considering the similarity and rerank scores.
    """
    try:
        service = get_reasoning_service()

        mapping = {
            "target_control_id": request.mapping.target_control_id,
            "target_framework": request.mapping.target_framework,
            "text": request.mapping.text,
            "similarity_score": request.mapping.similarity_score,
            "rerank_score": request.mapping.rerank_score,
        }

        reasoning = await service.generate_reasoning(
            source_control_id=request.source_control_id,
            source_text=request.source_text,
            mapping=mapping,
        )

        return ReasoningResponse(
            sourceControlId=request.source_control_id,
            targetControlId=request.mapping.target_control_id,
            reasoning=reasoning,
            status="success",
        )

    except Exception as e:
        logger.error(f"Reasoning generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reasoning generation failed: {str(e)}")


@router.post("/reason/batch", response_model=BatchReasoningResponse)
async def generate_batch_reasoning(request: BatchReasoningRequest) -> BatchReasoningResponse:
    """
    Generate reasoning for multiple mappings.

    Each mapping is processed individually. Maximum 20 mappings per request.
    For more efficient processing of many mappings, consider /reason/consolidated.
    """
    if len(request.mappings) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 mappings per batch request",
        )

    try:
        service = get_reasoning_service()

        mappings = [
            {
                "target_control_id": m.target_control_id,
                "target_framework": m.target_framework,
                "text": m.text,
                "similarity_score": m.similarity_score,
                "rerank_score": m.rerank_score,
            }
            for m in request.mappings
        ]

        results_data = await service.generate_batch_reasoning(
            source_control_id=request.source_control_id,
            source_text=request.source_text,
            mappings=mappings,
        )

        results = []
        successful = 0
        failed = 0

        for result in results_data:
            results.append(
                ReasoningResponse(
                    sourceControlId=result["source_control_id"],
                    targetControlId=result["control_id"],
                    reasoning=result["reasoning"],
                    status=result["status"],
                )
            )

            if result["status"] == "success":
                successful += 1
            else:
                failed += 1

        return BatchReasoningResponse(
            results=results,
            total=len(request.mappings),
            successful=successful,
            failed=failed,
        )

    except Exception as e:
        logger.error(f"Batch reasoning generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch reasoning failed: {str(e)}")


@router.post("/reason/consolidated", response_model=ConsolidatedReasoningResponse)
async def generate_consolidated_reasoning(
    request: ConsolidatedReasoningRequest,
) -> ConsolidatedReasoningResponse:
    """
    Generate consolidated reasoning for multiple mappings in a single API call.

    More efficient than batch processing for multiple mappings, as it uses
    a single Bedrock API call. Maximum 10 mappings per request.
    """
    if len(request.mappings) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 mappings per consolidated request",
        )

    try:
        service = get_reasoning_service()

        mappings = [
            {
                "target_control_id": m.target_control_id,
                "target_framework": m.target_framework,
                "text": m.text,
                "similarity_score": m.similarity_score,
                "rerank_score": m.rerank_score,
            }
            for m in request.mappings
        ]

        consolidated = await service.generate_consolidated_reasoning(
            source_control_id=request.source_control_id,
            source_text=request.source_text,
            mappings=mappings,
        )

        return ConsolidatedReasoningResponse(
            sourceControlId=request.source_control_id,
            consolidatedReasoning=consolidated,
            mappingCount=len(request.mappings),
            status="success",
        )

    except Exception as e:
        logger.error(f"Consolidated reasoning generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Consolidated reasoning failed: {str(e)}")
