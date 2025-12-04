"""NexusApplicationInterface module.

This package provides data models and interfaces for the Nexus application.
"""

from nexus_application_interface.api import v1

# Re-export commonly used v1 models at package level for convenience
from nexus_application_interface.api.v1 import (
    Control,
    Framework,
    Mapping,
    MappingReview,
    Enrichment,
    Job,
    Feedback,
    ControlStatus,
    FrameworkStatus,
    MappingStatus,
    JobStatus,
    AccessRole,
    CreatorInfo,
    HumanCreator,
    MachineCreator,
)

__all__ = [
    # API version namespace
    "v1",
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
]
