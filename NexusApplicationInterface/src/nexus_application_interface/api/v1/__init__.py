"""API v1 models for Nexus Application."""

from nexus_application_interface.api.v1.models import (
    Control,
    Framework,
    Mapping,
    MappingReview,
    Enrichment,
    Job,
    Feedback,
)
from nexus_application_interface.api.v1.models.enums import (
    ControlStatus,
    FrameworkStatus,
    MappingStatus,
    JobStatus,
    AccessRole,
)
from nexus_application_interface.api.v1.models.creators import (
    CreatorInfo,
    HumanCreator,
    MachineCreator,
    CustomCreator,
    MachineDetails,
)
from nexus_application_interface.api.v1.models.requests import (
    FrameworkCreateRequest,
    ControlCreateRequest,
    ControlUpdateRequest,
    BatchControlItem,
    BatchControlsCreateRequest,
    BatchArchiveRequest,
    MappingCreateItem,
    BatchMappingsCreateRequest,
    ReviewCreateRequest,
    ReviewUpdateRequest,
    FeedbackCreateRequest,
    FeedbackUpdateRequest,
)

__all__ = [
    # Core models
    "Control",
    "Framework",
    "Mapping",
    "MappingReview",
    "Enrichment",
    "Job",
    "Feedback",
    # Enums
    "ControlStatus",
    "FrameworkStatus",
    "MappingStatus",
    "JobStatus",
    "AccessRole",
    # Creator types
    "CreatorInfo",
    "HumanCreator",
    "MachineCreator",
    "CustomCreator",
    "MachineDetails",
    # Request models
    "FrameworkCreateRequest",
    "ControlCreateRequest",
    "ControlUpdateRequest",
    "BatchControlItem",
    "BatchControlsCreateRequest",
    "BatchArchiveRequest",
    "MappingCreateItem",
    "BatchMappingsCreateRequest",
    "ReviewCreateRequest",
    "ReviewUpdateRequest",
    "FeedbackCreateRequest",
    "FeedbackUpdateRequest",
]
