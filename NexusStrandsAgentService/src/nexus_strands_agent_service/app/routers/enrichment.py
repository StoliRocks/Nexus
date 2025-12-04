"""Enrichment API router - Control enrichment via multi-agent system."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nexus_strands_agent_service.app.services.enrichment_service import EnrichmentService

logger = logging.getLogger(__name__)

router = APIRouter()


class ControlInput(BaseModel):
    """Input model for a single control to enrich."""

    short_id: str = Field(..., alias="shortId", description="Control identifier")
    title: str = Field(default="", description="Control title")
    description: str = Field(default="", description="Control description text")
    supplemental_guidance: Optional[str] = Field(
        default=None, alias="supplementalGuidance", description="Additional guidance"
    )

    class Config:
        populate_by_name = True


class FrameworkMetadata(BaseModel):
    """Framework metadata for enrichment context."""

    framework_name: str = Field(..., alias="frameworkName", description="Framework name")
    framework_version: str = Field(..., alias="frameworkVersion", description="Framework version")

    class Config:
        populate_by_name = True


class EnrichmentRequest(BaseModel):
    """Request model for control enrichment."""

    metadata: FrameworkMetadata = Field(..., description="Framework metadata")
    control: ControlInput = Field(..., description="Control to enrich")
    framework_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="frameworkProfile",
        description="Pre-generated framework profile for enhanced enrichment",
    )

    class Config:
        populate_by_name = True


class BatchEnrichmentRequest(BaseModel):
    """Request model for batch control enrichment."""

    metadata: FrameworkMetadata = Field(..., description="Framework metadata")
    controls: List[ControlInput] = Field(..., description="Controls to enrich (max 10)")
    framework_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="frameworkProfile",
        description="Pre-generated framework profile",
    )

    class Config:
        populate_by_name = True


class ProfileGenerationRequest(BaseModel):
    """Request model for generating a framework profile."""

    framework_name: str = Field(..., alias="frameworkName", description="Framework name")
    sample_controls: List[ControlInput] = Field(
        ..., alias="sampleControls", description="Sample controls for profile generation (3-5)"
    )

    class Config:
        populate_by_name = True


class EnrichmentResponse(BaseModel):
    """Response model for control enrichment."""

    control_id: str = Field(..., alias="controlId", description="Control identifier")
    enriched_interpretation: Dict[str, Any] = Field(
        ..., alias="enrichedInterpretation", description="Enriched control interpretation"
    )
    agent_outputs: Optional[Dict[str, Any]] = Field(
        default=None, alias="agentOutputs", description="Individual agent outputs"
    )
    framework_profile_applied: Optional[Dict[str, Any]] = Field(
        default=None, alias="frameworkProfileApplied", description="Profile info if applied"
    )
    status: str = Field(..., description="Processing status (success/failed)")

    class Config:
        populate_by_name = True


class BatchEnrichmentResponse(BaseModel):
    """Response model for batch enrichment."""

    results: List[EnrichmentResponse] = Field(..., description="Enrichment results")
    total: int = Field(..., description="Total controls processed")
    successful: int = Field(..., description="Successfully processed count")
    failed: int = Field(..., description="Failed count")


class ProfileResponse(BaseModel):
    """Response model for framework profile generation."""

    framework_name: str = Field(..., alias="frameworkName")
    profile: Dict[str, Any] = Field(..., description="Generated framework profile")
    status: str = Field(..., description="Generation status")

    class Config:
        populate_by_name = True


# Service instance (initialized on startup)
_enrichment_service: Optional[EnrichmentService] = None


def get_enrichment_service() -> EnrichmentService:
    """Get or create enrichment service instance."""
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = EnrichmentService()
    return _enrichment_service


@router.post("/enrich", response_model=EnrichmentResponse)
async def enrich_control(request: EnrichmentRequest) -> EnrichmentResponse:
    """
    Enrich a single control using the multi-agent system.

    The enrichment process uses 5 specialized agents + 1 master review agent:
    - Agent 1: Objective classification
    - Agent 2: Technical/Hybrid/Non-Technical filter
    - Agent 3: Primary AWS services identification
    - Agent 4: Security impact analysis
    - Agent 5: Validation requirements
    - Master: Review and consolidation
    """
    try:
        service = get_enrichment_service()

        # Convert Pydantic models to dicts for the processor
        metadata = {
            "frameworkName": request.metadata.framework_name,
            "frameworkVersion": request.metadata.framework_version,
        }
        control = {
            "shortId": request.control.short_id,
            "title": request.control.title,
            "description": request.control.description,
        }
        if request.control.supplemental_guidance:
            control["supplementalGuidance"] = request.control.supplemental_guidance

        result = await service.enrich_control(
            metadata=metadata,
            control=control,
            framework_profile=request.framework_profile,
        )

        return EnrichmentResponse(
            controlId=request.control.short_id,
            enrichedInterpretation=result.get("enriched_interpretation", {}),
            agentOutputs=result.get("agent_outputs"),
            frameworkProfileApplied=result.get("framework_profile_applied"),
            status=result.get("status", "success"),
        )

    except Exception as e:
        logger.error(f"Enrichment failed for {request.control.short_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.post("/enrich/batch", response_model=BatchEnrichmentResponse)
async def enrich_controls_batch(request: BatchEnrichmentRequest) -> BatchEnrichmentResponse:
    """
    Enrich multiple controls in batch.

    Maximum 10 controls per request. Controls are processed sequentially
    to avoid overwhelming the Bedrock API.
    """
    if len(request.controls) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 controls per batch request",
        )

    try:
        service = get_enrichment_service()

        metadata = {
            "frameworkName": request.metadata.framework_name,
            "frameworkVersion": request.metadata.framework_version,
        }

        results = []
        successful = 0
        failed = 0

        for control_input in request.controls:
            control = {
                "shortId": control_input.short_id,
                "title": control_input.title,
                "description": control_input.description,
            }
            if control_input.supplemental_guidance:
                control["supplementalGuidance"] = control_input.supplemental_guidance

            try:
                result = await service.enrich_control(
                    metadata=metadata,
                    control=control,
                    framework_profile=request.framework_profile,
                )

                results.append(
                    EnrichmentResponse(
                        controlId=control_input.short_id,
                        enrichedInterpretation=result.get("enriched_interpretation", {}),
                        agentOutputs=result.get("agent_outputs"),
                        frameworkProfileApplied=result.get("framework_profile_applied"),
                        status=result.get("status", "success"),
                    )
                )

                if result.get("status") == "success":
                    successful += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Enrichment failed for {control_input.short_id}: {e}")
                results.append(
                    EnrichmentResponse(
                        controlId=control_input.short_id,
                        enrichedInterpretation={"error": str(e)},
                        status="failed",
                    )
                )
                failed += 1

        return BatchEnrichmentResponse(
            results=results,
            total=len(request.controls),
            successful=successful,
            failed=failed,
        )

    except Exception as e:
        logger.error(f"Batch enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch enrichment failed: {str(e)}")


@router.post("/profile/generate", response_model=ProfileResponse)
async def generate_framework_profile(request: ProfileGenerationRequest) -> ProfileResponse:
    """
    Generate a framework profile from sample controls.

    The profile is used to enhance agent prompts with framework-specific
    context, improving enrichment quality and consistency.

    Provide 3-5 representative sample controls for best results.
    """
    if len(request.sample_controls) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 sample controls required for profile generation",
        )

    if len(request.sample_controls) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 sample controls for profile generation",
        )

    try:
        service = get_enrichment_service()

        sample_controls = [
            {
                "shortId": c.short_id,
                "title": c.title,
                "description": c.description,
            }
            for c in request.sample_controls
        ]

        profile = await service.generate_framework_profile(
            framework_name=request.framework_name,
            sample_controls=sample_controls,
        )

        return ProfileResponse(
            frameworkName=request.framework_name,
            profile=profile,
            status="success",
        )

    except Exception as e:
        logger.error(f"Profile generation failed for {request.framework_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Profile generation failed: {str(e)}")
