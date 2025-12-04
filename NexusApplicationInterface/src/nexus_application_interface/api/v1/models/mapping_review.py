"""MappingReview model for the mapping-reviews DynamoDB table."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union, Literal, List

from nexus_application_interface.api.v1.models.creators import CreatorInfo


class ScoreValue(BaseModel):
    """Individual score value with range and source information."""
    value: str
    range_min: int = Field(alias="rangeMin")
    range_max: int = Field(alias="rangeMax")
    source: CreatorInfo

    class Config:
        populate_by_name = True


class ModelConfidenceScore(BaseModel):
    """ML model confidence score."""
    type: Literal["ModelConfidenceScore"] = "ModelConfidenceScore"
    scores: List[ScoreValue]

    class Config:
        populate_by_name = True


class LabelingScore(BaseModel):
    """Human labeling score."""
    type: Literal["LabelingScore"] = "LabelingScore"
    scores: List[ScoreValue]

    class Config:
        populate_by_name = True


class QAScore(BaseModel):
    """Quality assurance score."""
    type: Literal["QAScore"] = "QAScore"
    scores: List[ScoreValue]

    class Config:
        populate_by_name = True


# Discriminated union for mapping scores
MappingScore = Union[ModelConfidenceScore, LabelingScore, QAScore]


class MappingReview(BaseModel):
    """
    Model for a MappingReview in the mapping-reviews DynamoDB table.

    Stores mappings that are pending human review/labeling.
    Typically used for ML-predicted mappings that need human validation.

    Table Schema:
        - Partition Key: mappingKey
        - Sort Key: reviewKey
        - GSI: ReviewerIndex - PK: reviewerId, SK: submittedAt
    """

    # Primary Keys
    mapping_key: str = Field(
        alias="mappingKey",
        description="The mapping identifier (sorted controlKeys)"
    )
    review_key: str = Field(
        alias="reviewKey",
        description="Unique review identifier (e.g., timestamp-based)"
    )

    # Required Fields
    control_key: str = Field(
        alias="controlKey",
        description="Source control key"
    )
    mapped_control_key: str = Field(
        alias="mappedControlKey",
        description="Target control key"
    )
    status: str = Field(
        description="Review status (LABELING_IN_PROGRESS, REVIEW_IN_PROGRESS, etc.)"
    )
    submitted_at: str = Field(
        alias="submittedAt",
        description="ISO timestamp when submitted for review"
    )
    submitted_by: CreatorInfo = Field(
        alias="submittedBy",
        description="Who/what submitted this mapping for review"
    )
    mapping_scores: Optional[List[MappingScore]] = Field(
        default=None,
        alias="MappingScores",
        description="Collection of scores from different sources (ML, human labeling, QA)"
    )

    # Optional Fields
    reviewer_id: Optional[str] = Field(
        default=None,
        alias="reviewerId",
        description="ID of assigned reviewer"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="additionalInfo",
        description="Additional metadata about the review"
    )

    class Config:
        populate_by_name = True

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the MappingReview model to a DynamoDB item format."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "MappingReview":
        """Create a MappingReview instance from a DynamoDB item."""
        return cls.model_validate(item)

    @staticmethod
    def generate_review_key(timestamp: str, reviewer_id: Optional[str] = None) -> str:
        """
        Generate a review key.

        Args:
            timestamp: ISO format timestamp
            reviewer_id: Optional reviewer identifier

        Returns:
            Review key string
        """
        if reviewer_id:
            return f"{timestamp}#{reviewer_id}"
        return timestamp
