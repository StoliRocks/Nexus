"""Feedback model for the mapping-feedback DynamoDB table."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from nexus_application_interface.api.v1.models.enums import FeedbackType


class FeedbackEditHistory(BaseModel):
    """Edit history entry for feedback."""
    previous_label: str = Field(alias="previousLabel")
    previous_feedback: Dict[str, Any] = Field(alias="previousFeedback")
    edited_at: str = Field(alias="editedAt")

    class Config:
        populate_by_name = True


class Feedback(BaseModel):
    """
    Model for Feedback in the mapping-feedback DynamoDB table.

    Stores thumbs up/down feedback for mappings from users.

    Table Schema:
        - Partition Key: mappingKey
        - Sort Key: reviewerId
    """

    # Primary Keys
    mapping_key: str = Field(
        alias="mappingKey",
        description="The mapping identifier"
    )
    reviewer_id: str = Field(
        alias="reviewerId",
        description="ID of the feedback provider (sort key)"
    )

    # Required Fields
    feedback_provider_id: str = Field(
        alias="feedbackProviderId",
        description="ID of the user providing feedback"
    )
    label: str = Field(
        description="Feedback label (thumbs_up or thumbs_down)"
    )
    submitted_at: str = Field(
        alias="submittedAt",
        description="ISO timestamp when feedback was submitted"
    )

    # Optional Fields
    feedback: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional feedback details"
    )
    decision: Optional[bool] = Field(
        default=None,
        description="Boolean decision (True for thumbs_up)"
    )
    submitted_by: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="submittedBy",
        description="Details about who submitted the feedback"
    )
    edit_history: Optional[List[FeedbackEditHistory]] = Field(
        default=None,
        alias="editHistory",
        description="History of edits to this feedback"
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="ISO timestamp when feedback was last updated"
    )

    class Config:
        populate_by_name = True

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the Feedback model to a DynamoDB item format."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "Feedback":
        """Create a Feedback instance from a DynamoDB item."""
        return cls.model_validate(item)

    @property
    def is_positive(self) -> bool:
        """Check if feedback is positive (thumbs_up)."""
        return self.label == "thumbs_up"

    def to_api_response(self) -> Dict[str, Any]:
        """
        Convert to API response format.

        Returns:
            Dict suitable for API Gateway response.
        """
        response: Dict[str, Any] = {
            "mappingKey": self.mapping_key,
            "feedbackId": self.reviewer_id,
            "feedbackProviderId": self.feedback_provider_id,
            "label": self.label,
            "submittedAt": self.submitted_at,
        }
        if self.feedback:
            response["feedback"] = self.feedback
        if self.decision is not None:
            response["decision"] = self.decision
        return response
