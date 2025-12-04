"""Job updater business logic.

Updates job records with workflow results or errors.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)

JOB_TABLE_NAME = os.environ.get("JOB_TABLE_NAME", "MappingJobs")


class JobUpdaterService:
    """Service class for job status update operations."""

    def __init__(
        self,
        dynamodb_resource: Any = None,
        job_table_name: Optional[str] = None,
    ):
        """
        Initialize the job updater service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing).
            job_table_name: Optional table name override.
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.job_table_name = job_table_name or JOB_TABLE_NAME
        self.job_table = self.dynamodb.Table(self.job_table_name)

    def update_job_completed(
        self,
        job_id: str,
        mappings: List[dict],
        reasoning_results: List[dict],
    ) -> Dict[str, Any]:
        """
        Update job record with successful results.

        Args:
            job_id: Job identifier.
            mappings: List of mapping results from science orchestrator.
            reasoning_results: List of reasoning results from reasoning agent.

        Returns:
            Dict with job_id, status, mapping_count.
        """
        # Merge mappings with reasoning
        reasoning_map = {r["control_id"]: r["reasoning"] for r in reasoning_results}

        enriched_mappings = [
            {
                "target_control_id": m.get("target_control_id") or m.get("target_control_key"),
                "target_control_key": m.get("target_control_key") or m.get("target_control_id"),
                "target_framework": m.get("target_framework"),
                "target_framework_key": m.get("target_framework_key"),
                "similarity_score": m.get("similarity_score"),
                "rerank_score": m.get("rerank_score"),
                "text": m.get("text", ""),
                "reasoning": reasoning_map.get(
                    m.get("target_control_id") or m.get("target_control_key"), ""
                ),
            }
            for m in mappings
        ]

        now = datetime.utcnow().isoformat()

        self.job_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="""
                SET #status = :status,
                    updated_at = :updated_at,
                    mappings = :mappings,
                    completed_at = :completed_at
            """,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "COMPLETED",
                ":updated_at": now,
                ":mappings": enriched_mappings,
                ":completed_at": now,
            },
        )

        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "mapping_count": len(enriched_mappings),
        }

    def update_job_failed(
        self,
        job_id: str,
        error: Any,
    ) -> Dict[str, Any]:
        """
        Update job record with failure.

        Args:
            job_id: Job identifier.
            error: Error dict or string from Step Functions.

        Returns:
            Dict with job_id, status, error.
        """
        # Extract error message from various formats
        if isinstance(error, dict):
            error_message = error.get("Cause") or error.get("message") or str(error)
        else:
            error_message = str(error)

        now = datetime.utcnow().isoformat()

        self.job_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="""
                SET #status = :status,
                    updated_at = :updated_at,
                    error_message = :error_message,
                    failed_at = :failed_at
            """,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "FAILED",
                ":updated_at": now,
                ":error_message": error_message,
                ":failed_at": now,
            },
        )

        return {
            "job_id": job_id,
            "status": "FAILED",
            "error": error_message,
        }
