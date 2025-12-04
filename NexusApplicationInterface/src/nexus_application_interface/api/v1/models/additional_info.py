"""Additional info polymorphic models for Control, Framework, and Mapping entities."""

from pydantic import BaseModel, Field
from typing import Literal, Union, Optional, List, Dict, Any

from nexus_application_interface.api.v1.models.enums import (
    ControlBehavior,
    ControlSeverity,
    RegionScope,
)
from nexus_application_interface.api.v1.models.aws_catalog import (
    ImplementationDetails,
    ControlParameter,
    RegionConfiguration,
)


# ============================================================================
# AWS Control Catalog Additional Info
# ============================================================================

class AWSControlCatalogAdditionalInfo(BaseModel):
    """
    Additional information for AWS Control Catalog controls.

    Contains AWS-specific metadata from the Control Catalog API that doesn't
    map directly to the base Control model fields.
    """
    type: Literal["AWSControlCatalog"] = "AWSControlCatalog"
    aws_arn: Optional[str] = Field(
        default=None,
        alias="AwsArn",
        description="Original AWS Control Catalog ARN"
    )
    aliases: Optional[List[str]] = Field(
        default=None,
        alias="Aliases",
        description="Alternative identifiers (e.g., CT.CODEBUILD.PR.3, SH.S3.1)"
    )
    behavior: Optional[ControlBehavior] = Field(
        default=None,
        alias="Behavior",
        description="Control's functional behavior (PREVENTIVE, PROACTIVE, or DETECTIVE)"
    )
    create_time: Optional[str] = Field(
        default=None,
        alias="CreateTime",
        description="Timestamp when control was released as a governance capability"
    )
    governed_resources: Optional[List[str]] = Field(
        default=None,
        alias="GovernedResources",
        description="AWS CloudFormation resource types governed by this control"
    )
    implementation: Optional[ImplementationDetails] = Field(
        default=None,
        alias="Implementation",
        description="Implementation details showing the underlying implementation type"
    )
    parameters: Optional[List[ControlParameter]] = Field(
        default=None,
        alias="Parameters",
        description="Parameters that the control supports"
    )
    region_configuration: Optional[RegionConfiguration] = Field(
        default=None,
        alias="RegionConfiguration",
        description="Scope and available deployment regions"
    )
    severity: Optional[ControlSeverity] = Field(
        default=None,
        alias="Severity",
        description="Control severity (LOW, MEDIUM, HIGH, or CRITICAL)"
    )

    class Config:
        populate_by_name = True


# ============================================================================
# Generic Additional Info Models
# ============================================================================

class ControlAdditionalInfo(BaseModel):
    """Additional information for controls."""
    type: Literal["ControlAdditionalInfo"] = "ControlAdditionalInfo"
    data: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class FrameworkAdditionalInfo(BaseModel):
    """Additional information for frameworks."""
    type: Literal["FrameworkAdditionalInfo"] = "FrameworkAdditionalInfo"
    download_links: Optional[Dict[str, str]] = Field(
        default=None,
        alias="downloadLinks"
    )

    class Config:
        populate_by_name = True


# Union type for Control/Framework additional info
AdditionalInfo = Union[
    ControlAdditionalInfo,
    FrameworkAdditionalInfo,
    AWSControlCatalogAdditionalInfo,
    Dict[str, Any]
]


# ============================================================================
# Mapping Additional Info Models
# ============================================================================

class ConfidenceScoreInfo(BaseModel):
    """Confidence score information for mappings."""
    type: Literal["confidence_score"] = "confidence_score"
    score: float
    range_min: float = Field(alias="rangeMin")
    range_max: float = Field(alias="rangeMax")
    calculated_by: str = Field(alias="calculatedBy")
    calculated_at: str = Field(alias="calculatedAt")

    class Config:
        populate_by_name = True


class MappingRelationshipInfo(BaseModel):
    """Relationship type information for mappings."""
    type: Literal["mapping_relationship"] = "mapping_relationship"
    relationship_type: str = Field(alias="relationshipType")
    description: str
    equivalence_level: str = Field(alias="equivalenceLevel")

    class Config:
        populate_by_name = True


class FrameworkContextInfo(BaseModel):
    """Framework context information for mappings."""
    type: Literal["framework_context"] = "framework_context"
    source_framework_version: str = Field(alias="sourceFrameworkVersion")
    target_framework_version: str = Field(alias="targetFrameworkVersion")
    frameworks_compared_at: str = Field(alias="frameworksComparedAt")

    class Config:
        populate_by_name = True


# Union type for Mapping additional info
MappingAdditionalInfo = Union[
    ConfidenceScoreInfo,
    MappingRelationshipInfo,
    FrameworkContextInfo,
    Dict[str, Any]
]
