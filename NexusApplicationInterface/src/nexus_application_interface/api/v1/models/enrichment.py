"""Enrichment model for the control-enrichments DynamoDB table."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from nexus_application_interface.api.v1.models.creators import CreatorInfo


class Enrichment(BaseModel):
    """
    Model for an Enrichment in the control-enrichments DynamoDB table.

    Enrichments provide enhanced text descriptions for controls that can
    optionally replace the control's default description.

    Table Schema:
        - Partition Key: controlKey
        - Sort Key: version
    """

    # Primary Keys
    control_key: str = Field(
        alias="controlKey",
        description="Foreign key reference to control in framework-controls table"
    )
    version: str = Field(
        description="Enrichment version (e.g., '1.0', '2.0')"
    )

    # Required Fields
    enrichment_text: str = Field(
        alias="enrichmentText",
        description="Enhanced text description to replace control description"
    )
    created_by: CreatorInfo = Field(
        alias="createdBy",
        description="Details about enrichment creator"
    )

    # Optional Fields
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="additionalInfo",
        description="Additional metadata about the enrichment"
    )

    class Config:
        populate_by_name = True

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the Enrichment model to a DynamoDB item format."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "Enrichment":
        """Create an Enrichment instance from a DynamoDB item."""
        return cls.model_validate(item)
