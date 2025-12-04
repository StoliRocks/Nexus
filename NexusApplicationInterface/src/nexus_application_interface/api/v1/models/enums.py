"""Enum definitions for Nexus API v1 models."""

from enum import Enum


class ControlStatus(str, Enum):
    """Valid control status values."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class FrameworkStatus(str, Enum):
    """Valid framework status values."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class MappingStatus(str, Enum):
    """Valid mapping status values."""
    LABELING_IN_PROGRESS = "LABELING_IN_PROGRESS"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEW_IN_PROGRESS = "REVIEW_IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class JobStatus(str, Enum):
    """Valid job status values."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AccessRole(str, Enum):
    """Valid human role values."""
    ADMIN = "ADMIN"
    CONSULTANT = "CONSULTANT"
    LABELER = "LABELER"
    QA = "QA"
    SERVICE = "SERVICE"


class ControlBehavior(str, Enum):
    """Valid AWS Control Catalog behavior values."""
    PREVENTIVE = "PREVENTIVE"
    PROACTIVE = "PROACTIVE"
    DETECTIVE = "DETECTIVE"


class ControlSeverity(str, Enum):
    """Valid AWS Control Catalog severity values."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RegionScope(str, Enum):
    """Valid AWS region scope values."""
    REGIONAL = "REGIONAL"
    GLOBAL = "GLOBAL"


class FeedbackType(str, Enum):
    """Valid feedback type values."""
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"
