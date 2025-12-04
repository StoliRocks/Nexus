"""Mapping model for the control-mappings DynamoDB table."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import re

from nexus_application_interface.api.v1.models.enums import MappingStatus
from nexus_application_interface.api.v1.models.creators import CreatorInfo, MachineCreator, HumanCreator
from nexus_application_interface.api.v1.models.additional_info import MappingAdditionalInfo


class Mapping(BaseModel):
    """
    Model for a Mapping in the control-mappings DynamoDB table.

    Mappings represent bidirectional equivalence relationships between controls.
    When created, two entries are written atomically (A->B and B->A).

    Table Schema:
        - Partition Key: controlKey
        - Sort Key: mappedControlKey
        - GSIs: MappingKeyIndex, StatusIndex, WorkflowIndex, ControlStatusIndex
    """

    # Primary Keys
    control_key: str = Field(
        alias="controlKey",
        description="Source control key"
    )
    mapped_control_key: str = Field(
        alias="mappedControlKey",
        description="Target control key"
    )

    # Required Fields
    mapping_key: str = Field(
        alias="mappingKey",
        description="System generated unique mapping identifier (sorted controlKeys)"
    )
    arn: str = Field(
        description="System generated ARN, region and account are optional"
    )
    mapping_workflow_key: str = Field(
        alias="mappingWorkflowKey",
        description="Unique identifier of workflow that created this mapping"
    )
    timestamp: str = Field(
        description="ISO format timestamp for creation/update"
    )
    status: MappingStatus = Field(
        description="Current status of the mapping"
    )
    created_by: CreatorInfo = Field(
        alias="createdBy",
        description="Details about mapping creator"
    )
    last_modified_by: CreatorInfo = Field(
        alias="lastModifiedBy",
        description="Details about when the mapping was last updated"
    )

    # Optional Fields
    additional_info: Optional[List[MappingAdditionalInfo]] = Field(
        default=None,
        alias="additionalInfo",
        description="Collection of polymorphic objects with additional information"
    )

    class Config:
        populate_by_name = True
        use_enum_values = True

    @field_validator('control_key', 'mapped_control_key')
    @classmethod
    def validate_control_keys_differ(cls, v: str, info) -> str:
        """Validate that control keys are not empty and differ from each other."""
        if not v or not v.strip():
            raise ValueError("Control keys cannot be empty")

        if info.data.get('control_key') and info.data.get('mapped_control_key'):
            if info.data['control_key'] == info.data['mapped_control_key']:
                raise ValueError("control_key and mapped_control_key must be different")

        return v

    @field_validator('mapping_key')
    @classmethod
    def validate_mapping_key_format(cls, v: str, info) -> str:
        """Validate that mapping_key follows the normalized format."""
        if '#' not in v:
            raise ValueError("mapping_key must contain '#' separator")

        parts = v.split('#')
        if len(parts) < 2:
            raise ValueError("mapping_key must have at least two parts separated by '#'")

        return v

    @field_validator('arn')
    @classmethod
    def validate_mapping_arn(cls, v: str, info) -> str:
        """
        Validate that ARN follows the pattern:
        - arn:aws:nexus:[region:accountId]:mapping:mappingKey
        - arn:aws:nexus::mapping:mappingKey (when region/accountId optional)
        and that mappingKey matches mapping_key.
        """
        pattern = r'^arn:aws:nexus:(\[[^\]]+\]:|::)mapping:.+$'

        if not re.match(pattern, v):
            raise ValueError(
                "ARN must match pattern: arn:aws:nexus:[region:accountId]:mapping:mappingKey "
                "or arn:aws:nexus::mapping:mappingKey"
            )

        arn_mapping_key = v.split(':mapping:')[-1]
        mapping_key = info.data.get('mapping_key')

        if mapping_key and arn_mapping_key != mapping_key:
            raise ValueError(
                f"ARN mappingKey '{arn_mapping_key}' must match mapping_key '{mapping_key}'"
            )

        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the Mapping model to a DynamoDB item format."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "Mapping":
        """Create a Mapping instance from a DynamoDB item."""
        return cls.model_validate(item)

    @staticmethod
    def generate_mapping_key(control_key_1: str, control_key_2: str) -> str:
        """
        Generate a normalized mapping key by sorting control keys alphabetically.

        This ensures both A->B and B->A mappings share the same mappingKey.

        Args:
            control_key_1: First control key
            control_key_2: Second control key

        Returns:
            Normalized mapping key in format: sorted_key1#sorted_key2

        Raises:
            ValueError: If control keys are the same
        """
        if control_key_1 == control_key_2:
            raise ValueError("Cannot create mapping between same control")

        keys = sorted([control_key_1, control_key_2])
        return f"{keys[0]}#{keys[1]}"

    @staticmethod
    def generate_workflow_key(creator: CreatorInfo) -> str:
        """
        Generate workflow key from creator information.

        Args:
            creator: CreatorInfo instance

        Returns:
            Workflow key string
        """
        if isinstance(creator, MachineCreator):
            model_name = creator.machine_details.model_name
            model_version = creator.machine_details.model_version
            return f"Science#{model_name}-{model_version}"
        elif isinstance(creator, HumanCreator):
            return f"Manual#{creator.role}"
        else:
            return "Custom#Unknown"

    @staticmethod
    def generate_arn(mapping_key: str, region: Optional[str] = None, account_id: Optional[str] = None) -> str:
        """
        Generate an ARN for a mapping.

        Args:
            mapping_key: The mapping key
            region: Optional AWS region
            account_id: Optional AWS account ID

        Returns:
            ARN string
        """
        if region and account_id:
            return f"arn:aws:nexus:[{region}:{account_id}]:mapping:{mapping_key}"
        return f"arn:aws:nexus::mapping:{mapping_key}"

    def create_reverse_mapping(self) -> "Mapping":
        """
        Create the reverse mapping (B->A from A->B).

        Returns:
            New Mapping instance with swapped control keys
        """
        return Mapping(
            controlKey=self.mapped_control_key,
            mappedControlKey=self.control_key,
            mappingKey=self.mapping_key,
            arn=self.arn,
            mappingWorkflowKey=self.mapping_workflow_key,
            timestamp=self.timestamp,
            status=self.status,
            createdBy=self.created_by,
            lastModifiedBy=self.last_modified_by,
            additionalInfo=self.additional_info
        )
