"""Status handler business logic."""

import logging
import os
from typing import Any, Dict, Optional

import boto3

from nexus_application_commons.dynamodb.response_builder import (
    success_response,
    not_found_response,
)

logger = logging.getLogger(__name__)

JOB_TABLE_NAME = os.environ.get("JOB_TABLE_NAME", "MappingJobs")


class StatusService:
    """Service class for job status query operations."""

    def __init__(self, dynamodb_resource: Optional[Any] = None, table_name: Optional[str] = None):
        """
        Initialize the status service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            table_name: Optional table name override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or JOB_TABLE_NAME
        self.table = self.dynamodb.Table(self.table_name)

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status and results.

        Args:
            job_id: Job identifier (mappingId).

        Returns:
            API response with job status and results (if completed).
        """
        job = self._get_job(job_id)
        if not job:
            return not_found_response("Mapping job", job_id)

        return success_response(self._build_job_response(job))

    def _get_job(self, job_id: str) -> Optional[dict]:
        """
        Fetch job record from DynamoDB.

        Args:
            job_id: Job identifier.

        Returns:
            Job record dict, or None if not found.
        """
        result = self.table.get_item(Key={"job_id": job_id})
        return result.get("Item")

    def _build_job_response(self, job: dict) -> dict:
        """
        Build response body from job record.

        Args:
            job: DynamoDB job record.

        Returns:
            Response dict with status, timestamps, and results (if completed).
        """
        response = {
            "mappingId": job["job_id"],
            "status": job["status"],
            "controlKey": job.get("control_key") or job.get("control_id"),
            "targetFrameworkKey": job.get("target_framework_key") or job.get("target_framework"),
            "createdAt": job.get("created_at"),
            "updatedAt": job.get("updated_at"),
        }

        # Include target_control_ids if present
        target_ids = job.get("target_control_ids")
        if target_ids:
            response["targetControlIds"] = target_ids

        # Include results for completed jobs
        if job["status"] == "COMPLETED":
            response["result"] = {
                "mappings": job.get("mappings", []),
            }
            # Include reasoning if present
            if job.get("reasoning"):
                response["result"]["reasoning"] = job.get("reasoning")

        # Include error for failed jobs
        elif job["status"] == "FAILED":
            response["error"] = job.get("error_message", "Unknown error")

        return response
