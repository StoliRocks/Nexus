"""AWS Control Catalog specific models."""

from pydantic import BaseModel, Field
from typing import Optional, List

from nexus_application_interface.api.v1.models.enums import RegionScope


class ImplementationDetails(BaseModel):
    """
    Implementation details for AWS Control Catalog controls.

    Indicates the underlying implementation type for a control.
    """
    type: str = Field(
        alias="Type",
        description="Implementation type (e.g., AWS::CloudFormation::Type::HOOK)"
    )
    identifier: Optional[str] = Field(
        default=None,
        alias="Identifier",
        description="Optional implementation identifier"
    )

    class Config:
        populate_by_name = True


class ControlParameter(BaseModel):
    """
    Parameter specification for AWS Control Catalog controls.

    Represents a parameter that a control supports.
    """
    name: str = Field(alias="Name", description="Parameter name")

    class Config:
        populate_by_name = True


class RegionConfiguration(BaseModel):
    """
    Region configuration for AWS Control Catalog controls.

    Includes the scope of the control and the Regions where it's available for deployment.
    """
    scope: RegionScope = Field(
        alias="Scope",
        description="Control scope (REGIONAL or GLOBAL)"
    )
    deployable_regions: List[str] = Field(
        alias="DeployableRegions",
        description="List of regions where control can be deployed"
    )

    class Config:
        populate_by_name = True
