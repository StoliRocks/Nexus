"""Control model for the framework-controls DynamoDB table."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import re

from nexus_application_interface.api.v1.models.enums import ControlStatus
from nexus_application_interface.api.v1.models.creators import CreatorInfo
from nexus_application_interface.api.v1.models.additional_info import AdditionalInfo


class Control(BaseModel):
    """
    Model for a Control in the framework-controls DynamoDB table.

    A control belongs to a framework and represents a safeguard or
    countermeasure prescribed for an information system.

    Table Schema:
        - Partition Key: frameworkKey
        - Sort Key: controlKey
        - GSIs: ControlKeyIndex, StatusIndex
    """

    # Primary Keys
    control_key: str = Field(
        alias="controlKey",
        description="System generated unique identifier for a control within Nexus"
    )
    framework_key: str = Field(
        alias="frameworkKey",
        description="Unique identifier of the framework the control belongs to"
    )

    # Required Fields
    control_id: str = Field(
        alias="controlId",
        description="Unique control identifier within the framework"
    )
    arn: str = Field(
        description="System generated ARN, region and account are optional"
    )
    control_version: str = Field(
        default="1.0",
        alias="controlVersion",
        description="Version of the control, defaults to 1.0"
    )
    status: ControlStatus = Field(
        description="Current status of the control (ACTIVE|ARCHIVED)"
    )
    title: str = Field(
        description="Control title"
    )
    description: str = Field(
        description="Control description"
    )
    created_by: CreatorInfo = Field(
        alias="createdBy",
        description="Details about control creator"
    )
    last_modified_by: CreatorInfo = Field(
        alias="lastModifiedBy",
        description="Details about when the control was last updated"
    )

    # Optional Fields
    additional_info: Optional[List[AdditionalInfo]] = Field(
        default=None,
        alias="additionalInfo",
        description="Collection of polymorphic objects with additional information"
    )

    class Config:
        populate_by_name = True
        use_enum_values = True

    @field_validator('arn')
    @classmethod
    def validate_control_arn(cls, v: str, info) -> str:
        """
        Validate that ARN follows the pattern:
        - arn:aws:nexus:[region:accountId]:control:controlKey
        - arn:aws:nexus::control:controlKey (when region/accountId optional)
        and that controlKey matches control_key.
        """
        pattern = r'^arn:aws:nexus:(\[[^\]]+\]:|::)control:.+$'

        if not re.match(pattern, v):
            raise ValueError(
                "ARN must match pattern: arn:aws:nexus:[region:accountId]:control:controlKey "
                "or arn:aws:nexus::control:controlKey"
            )

        arn_control_key = v.split(':control:')[-1]
        control_key = info.data.get('control_key')

        if control_key and arn_control_key != control_key:
            raise ValueError(
                f"ARN controlKey '{arn_control_key}' must match control_key '{control_key}'"
            )

        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the Control model to a DynamoDB item format."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "Control":
        """Create a Control instance from a DynamoDB item."""
        return cls.model_validate(item)

    @staticmethod
    def generate_control_key(framework_key: str, control_id: str) -> str:
        """
        Generate a control_key from framework_key and control_id.

        Args:
            framework_key: Framework key in format frameworkName#version
            control_id: Control identifier within the framework

        Returns:
            Control key in format: frameworkKey#controlId
        """
        return f"{framework_key}#{control_id}"

    @staticmethod
    def generate_arn(control_key: str, region: Optional[str] = None, account_id: Optional[str] = None) -> str:
        """
        Generate an ARN for a control.

        Args:
            control_key: The control key
            region: Optional AWS region
            account_id: Optional AWS account ID

        Returns:
            ARN string
        """
        if region and account_id:
            return f"arn:aws:nexus:[{region}:{account_id}]:control:{control_key}"
        return f"arn:aws:nexus::control:{control_key}"
