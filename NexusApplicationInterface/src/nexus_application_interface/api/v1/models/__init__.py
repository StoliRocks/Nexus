"""Data models for Nexus API v1."""

# Database/Response models
from nexus_application_interface.api.v1.models.control import Control
from nexus_application_interface.api.v1.models.framework import Framework
from nexus_application_interface.api.v1.models.mapping import Mapping
from nexus_application_interface.api.v1.models.mapping_review import MappingReview
from nexus_application_interface.api.v1.models.enrichment import Enrichment
from nexus_application_interface.api.v1.models.job import Job
from nexus_application_interface.api.v1.models.feedback import Feedback

# Request models for API input validation
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
    # Database/Response models
    "Control",
    "Framework",
    "Mapping",
    "MappingReview",
    "Enrichment",
    "Job",
    "Feedback",
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
