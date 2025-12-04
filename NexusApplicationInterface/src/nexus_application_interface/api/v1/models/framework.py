"""Framework model for the frameworks DynamoDB table."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import re

from nexus_application_interface.api.v1.models.enums import FrameworkStatus
from nexus_application_interface.api.v1.models.creators import CreatorInfo
from nexus_application_interface.api.v1.models.additional_info import AdditionalInfo


class Framework(BaseModel):
    """
    Model for a Framework in the frameworks DynamoDB table.

    A framework is a collection of controls.

    Table Schema:
        - Partition Key: frameworkName
        - Sort Key: version
        - GSIs: FrameworkKeyIndex, StatusIndex
    """

    # Primary Keys
    framework_name: str = Field(
        alias="frameworkName",
        description="Name of the framework"
    )
    version: str = Field(
        description="Version of the framework"
    )

    # Required Fields
    framework_key: str = Field(
        alias="frameworkKey",
        description="System generated unique framework identifier (frameworkName#version)"
    )
    arn: str = Field(
        description="System generated ARN, region and account are optional"
    )
    status: FrameworkStatus = Field(
        description="Current status (ACTIVE|ARCHIVED)"
    )
    created_by: CreatorInfo = Field(
        alias="createdBy",
        description="Details about framework creator"
    )
    last_modified_by: CreatorInfo = Field(
        alias="lastModifiedBy",
        description="Details about when the framework was last updated"
    )

    # Optional Fields
    description: Optional[str] = Field(
        default=None,
        description="Description of the framework"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of the standard"
    )
    uri: Optional[str] = Field(
        default=None,
        description="URI of the framework"
    )
    additional_info: Optional[List[AdditionalInfo]] = Field(
        default=None,
        alias="additionalInfo",
        description="Collection of polymorphic objects with additional information"
    )

    class Config:
        populate_by_name = True
        use_enum_values = True

    @field_validator('framework_key')
    @classmethod
    def validate_framework_key(cls, v: str, info) -> str:
        """Validate that framework_key follows the pattern: frameworkName#version"""
        if '#' not in v:
            raise ValueError("framework_key must follow pattern: frameworkName#version")
        return v

    @field_validator('arn')
    @classmethod
    def validate_framework_arn(cls, v: str, info) -> str:
        """
        Validate that ARN follows the pattern:
        - arn:aws:nexus:[region:accountId]:framework:frameworkId
        - arn:aws:nexus::framework:frameworkId (when region/accountId optional)
        and that frameworkId matches framework_key.
        """
        pattern = r'^arn:aws:nexus:(\[[^\]]+\]:|::)framework:.+$'

        if not re.match(pattern, v):
            raise ValueError(
                "ARN must match pattern: arn:aws:nexus:[region:accountId]:framework:frameworkId "
                "or arn:aws:nexus::framework:frameworkId"
            )

        arn_framework_id = v.split(':framework:')[-1]
        framework_key = info.data.get('framework_key')

        if framework_key and arn_framework_id != framework_key:
            raise ValueError(
                f"ARN frameworkId '{arn_framework_id}' must match framework_key '{framework_key}'"
            )

        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the Framework model to a DynamoDB item format."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "Framework":
        """Create a Framework instance from a DynamoDB item."""
        return cls.model_validate(item)

    @staticmethod
    def generate_framework_key(framework_name: str, version: str) -> str:
        """
        Generate a framework_key from framework_name and version.

        Args:
            framework_name: Name of the framework
            version: Version of the framework

        Returns:
            Framework key in format: frameworkName#version
        """
        return f"{framework_name}#{version}"

    @staticmethod
    def generate_arn(framework_key: str, region: Optional[str] = None, account_id: Optional[str] = None) -> str:
        """
        Generate an ARN for a framework.

        Args:
            framework_key: The framework key
            region: Optional AWS region
            account_id: Optional AWS account ID

        Returns:
            ARN string
        """
        if region and account_id:
            return f"arn:aws:nexus:[{region}:{account_id}]:framework:{framework_key}"
        return f"arn:aws:nexus::framework:{framework_key}"
