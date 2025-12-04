"""Request models for API input validation.

These models represent the request body schemas for API endpoints.
They contain only the fields that users can provide, with appropriate
validation and defaults.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List


# ============================================================================
# Framework Request Models
# ============================================================================


class FrameworkCreateRequest(BaseModel):
    """Request body for creating or updating a framework (PUT /frameworks/{name}/{version})."""

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Description of the framework"
    )
    source: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Source of the standard (e.g., NIST, ISO)"
    )
    uri: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="URI reference for the framework"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="additionalInfo",
        description="Additional metadata"
    )

    class Config:
        populate_by_name = True


# ============================================================================
# Control Request Models
# ============================================================================


class ControlCreateRequest(BaseModel):
    """Request body for creating or updating a control (PUT /controls/{controlId})."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Control title (required)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Control description"
    )
    control_guide: Optional[str] = Field(
        default=None,
        alias="controlGuide",
        max_length=10000,
        description="Implementation guidance"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="additionalInfo",
        description="Additional metadata"
    )

    class Config:
        populate_by_name = True


class ControlUpdateRequest(BaseModel):
    """Request body for updating a control (same as create but title is optional)."""

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Control title"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Control description"
    )
    control_guide: Optional[str] = Field(
        default=None,
        alias="controlGuide",
        max_length=10000,
        description="Implementation guidance"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="additionalInfo",
        description="Additional metadata"
    )

    class Config:
        populate_by_name = True


class BatchControlItem(BaseModel):
    """Single control item in a batch create request."""

    control_id: str = Field(
        ...,
        alias="controlId",
        min_length=1,
        max_length=100,
        description="Control identifier"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Control title"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Control description"
    )
    control_guide: Optional[str] = Field(
        default=None,
        alias="controlGuide",
        max_length=10000,
        description="Implementation guidance"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="additionalInfo",
        description="Additional metadata"
    )

    class Config:
        populate_by_name = True


class BatchControlsCreateRequest(BaseModel):
    """Request body for batch creating controls (POST /batchControls)."""

    controls: List[BatchControlItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Controls to create (max 100)"
    )

    @field_validator('controls')
    @classmethod
    def validate_controls_limit(cls, v: List[BatchControlItem]) -> List[BatchControlItem]:
        if len(v) > 100:
            raise ValueError("Maximum 100 controls per batch request")
        return v


class BatchArchiveRequest(BaseModel):
    """Request body for batch archiving controls (POST /controls/batchArchive)."""

    control_ids: List[str] = Field(
        ...,
        alias="controlIds",
        min_length=1,
        max_length=100,
        description="Control IDs to archive (max 100)"
    )

    class Config:
        populate_by_name = True

    @field_validator('control_ids')
    @classmethod
    def validate_control_ids_limit(cls, v: List[str]) -> List[str]:
        if len(v) > 100:
            raise ValueError("Maximum 100 control IDs per batch archive request")
        return v


# ============================================================================
# Mapping Request Models
# ============================================================================


class MappingCreateItem(BaseModel):
    """Single mapping item for batch create."""

    source_control_key: str = Field(
        ...,
        alias="sourceControlKey",
        description="Source control key"
    )
    target_control_key: str = Field(
        ...,
        alias="targetControlKey",
        description="Target control key"
    )
    similarity_score: Optional[float] = Field(
        default=None,
        alias="similarityScore",
        ge=0.0,
        le=1.0,
        description="Embedding similarity score (0-1)"
    )
    rerank_score: Optional[float] = Field(
        default=None,
        alias="rerankScore",
        ge=0.0,
        le=1.0,
        description="Cross-encoder rerank score (0-1)"
    )
    reasoning: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Human-readable rationale for the mapping"
    )

    class Config:
        populate_by_name = True

    @field_validator('target_control_key')
    @classmethod
    def validate_different_keys(cls, v: str, info) -> str:
        source = info.data.get('source_control_key')
        if source and source == v:
            raise ValueError("source_control_key and target_control_key must be different")
        return v


class BatchMappingsCreateRequest(BaseModel):
    """Request body for batch creating mappings (POST /batchMappings)."""

    mappings: List[MappingCreateItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Mappings to create (max 100)"
    )

    @field_validator('mappings')
    @classmethod
    def validate_mappings_limit(cls, v: List[MappingCreateItem]) -> List[MappingCreateItem]:
        if len(v) > 100:
            raise ValueError("Maximum 100 mappings per batch request")
        return v


# ============================================================================
# Review Request Models
# ============================================================================


class ReviewCreateRequest(BaseModel):
    """Request body for creating a review (POST /reviews)."""

    reviewer_id: str = Field(
        ...,
        alias="reviewerId",
        min_length=1,
        max_length=200,
        description="Reviewer identifier (required)"
    )
    correct: bool = Field(
        ...,
        description="Whether the mapping is correct (required)"
    )
    is_final_review: bool = Field(
        default=False,
        alias="isFinalReview",
        description="Whether this is the final review"
    )
    feedback: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional feedback details"
    )

    class Config:
        populate_by_name = True


class ReviewUpdateRequest(BaseModel):
    """Request body for updating a review (PUT /reviews/{reviewId})."""

    correct: Optional[bool] = Field(
        default=None,
        description="Updated correctness assessment"
    )
    is_final_review: Optional[bool] = Field(
        default=None,
        alias="isFinalReview",
        description="Updated final review status"
    )
    feedback: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated feedback details"
    )

    class Config:
        populate_by_name = True

    def has_updates(self) -> bool:
        """Check if any field is being updated."""
        return any([
            self.correct is not None,
            self.is_final_review is not None,
            self.feedback is not None,
        ])


# ============================================================================
# Feedback Request Models
# ============================================================================


class FeedbackCreateRequest(BaseModel):
    """Request body for creating feedback (POST /feedbacks)."""

    feedback_provider_id: str = Field(
        ...,
        alias="feedbackProviderId",
        min_length=1,
        max_length=200,
        description="Feedback provider identifier (required)"
    )
    label: str = Field(
        ...,
        description="Feedback label: 'thumbs_up' or 'thumbs_down' (required)"
    )
    feedback: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional feedback details"
    )

    class Config:
        populate_by_name = True

    @field_validator('label')
    @classmethod
    def validate_label(cls, v: str) -> str:
        if v not in ('thumbs_up', 'thumbs_down'):
            raise ValueError("label must be 'thumbs_up' or 'thumbs_down'")
        return v

    @property
    def decision(self) -> bool:
        """Convert label to boolean decision."""
        return self.label == 'thumbs_up'


class FeedbackUpdateRequest(BaseModel):
    """Request body for updating feedback (PUT /feedbacks/{feedbackId})."""

    label: Optional[str] = Field(
        default=None,
        description="Updated feedback label"
    )
    feedback: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated feedback details"
    )

    class Config:
        populate_by_name = True

    @field_validator('label')
    @classmethod
    def validate_label(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('thumbs_up', 'thumbs_down'):
            raise ValueError("label must be 'thumbs_up' or 'thumbs_down'")
        return v

    def has_updates(self) -> bool:
        """Check if any field is being updated."""
        return self.label is not None or self.feedback is not None

    @property
    def decision(self) -> Optional[bool]:
        """Convert label to boolean decision if present."""
        if self.label is None:
            return None
        return self.label == 'thumbs_up'
