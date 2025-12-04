"""Creator models for tracking who created/modified entities."""

from pydantic import BaseModel, Field
from typing import Literal, Union

from nexus_application_interface.api.v1.models.enums import AccessRole


class MachineDetails(BaseModel):
    """Details about the machine that created/modified an entity."""
    model_name: str = Field(alias="modelName")
    model_version: str = Field(alias="modelVersion")

    class Config:
        populate_by_name = True


class HumanCreator(BaseModel):
    """Human creator information."""
    type: Literal["Human"] = "Human"
    alias: str
    role: AccessRole
    timestamp: str

    class Config:
        populate_by_name = True


class MachineCreator(BaseModel):
    """Machine creator information."""
    type: Literal["Machine"] = "Machine"
    timestamp: str
    machine_details: MachineDetails = Field(alias="machineDetails")

    class Config:
        populate_by_name = True


class CustomCreator(BaseModel):
    """Custom creator information for edge cases."""
    type: str
    timestamp: str

    class Config:
        populate_by_name = True


# Discriminated union for creator info
CreatorInfo = Union[HumanCreator, MachineCreator, CustomCreator]
