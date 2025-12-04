"""Job model for the jobs DynamoDB table."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from nexus_application_interface.api.v1.models.enums import JobStatus


class Job(BaseModel):
    """
    Model for a Job in the jobs DynamoDB table.

    Jobs track async mapping workflow executions.

    Table Schema:
        - Partition Key: job_id
        - TTL: ttl (7 days after creation)
    """

    # Primary Key
    job_id: str = Field(
        alias="jobId",
        description="Unique job identifier (UUID)"
    )

    # Required Fields
    status: JobStatus = Field(
        description="Current job status (PENDING, IN_PROGRESS, COMPLETED, FAILED)"
    )
    control_key: str = Field(
        alias="controlKey",
        description="Source control key for the mapping request"
    )
    target_framework_key: str = Field(
        alias="targetFrameworkKey",
        description="Target framework key (frameworkName#version)"
    )
    created_at: str = Field(
        alias="createdAt",
        description="ISO timestamp when job was created"
    )
    updated_at: str = Field(
        alias="updatedAt",
        description="ISO timestamp when job was last updated"
    )

    # Optional Fields
    target_control_ids: Optional[List[str]] = Field(
        default=None,
        alias="targetControlIds",
        description="Optional list of specific target control IDs"
    )
    ttl: Optional[int] = Field(
        default=None,
        description="TTL timestamp for DynamoDB auto-deletion"
    )
    mappings: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Resulting mappings when job completes"
    )
    error: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Error details if job fails"
    )

    class Config:
        populate_by_name = True
        use_enum_values = True

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the Job model to a DynamoDB item format."""
        # DynamoDB uses snake_case for job table
        item: Dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status,
            "control_key": self.control_key,
            "target_framework_key": self.target_framework_key,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.target_control_ids:
            item["target_control_ids"] = self.target_control_ids
        if self.ttl:
            item["ttl"] = self.ttl
        if self.mappings:
            item["mappings"] = self.mappings
        if self.error:
            item["error"] = self.error
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "Job":
        """Create a Job instance from a DynamoDB item."""
        return cls(
            jobId=item["job_id"],
            status=JobStatus(item["status"]),
            controlKey=item["control_key"],
            targetFrameworkKey=item["target_framework_key"],
            createdAt=item["created_at"],
            updatedAt=item["updated_at"],
            targetControlIds=item.get("target_control_ids"),
            ttl=item.get("ttl"),
            mappings=item.get("mappings"),
            error=item.get("error"),
        )

    def to_api_response(self) -> Dict[str, Any]:
        """
        Convert to API response format.

        Returns:
            Dict suitable for API Gateway response.
        """
        response: Dict[str, Any] = {
            "mappingId": self.job_id,
            "status": self.status,
            "controlKey": self.control_key,
            "targetFrameworkKey": self.target_framework_key,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.mappings:
            response["mappings"] = self.mappings
        if self.error:
            response["error"] = self.error
        return response
