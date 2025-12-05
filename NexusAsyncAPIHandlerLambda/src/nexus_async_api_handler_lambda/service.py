"""Async handler business logic.

Supports Nexus Database Schema:
- control_key: Full control key (frameworkKey#controlId)
- target_framework_key: Full target framework key (frameworkName#version)

Publishes mapping requests to SQS for durable processing.
Uses DAOs from NexusApplicationInterface and patterns from NexusApplicationCommons.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Key

from nexus_application_interface.api.v1 import Job
from nexus_application_interface.api.v1.models.enums import JobStatus
from nexus_application_commons.dynamodb.base_repository import BaseRepository

logger = logging.getLogger(__name__)

JOB_TABLE_NAME = os.environ.get("JOB_TABLE_NAME", "MappingJobs")
MAPPING_REQUEST_QUEUE_URL = os.environ.get("MAPPING_REQUEST_QUEUE_URL", "")
FRAMEWORKS_TABLE_NAME = os.environ.get("FRAMEWORKS_TABLE_NAME", "Frameworks")
CONTROLS_TABLE_NAME = os.environ.get("CONTROLS_TABLE_NAME", "FrameworkControls")
JOB_TTL_DAYS = 7

# Validation constants
MAX_CONTROL_KEY_LENGTH = 256
MAX_FRAMEWORK_KEY_LENGTH = 128
MAX_CONTROL_IDS_COUNT = 100
CONTROL_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+#.+$")
FRAMEWORK_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+$")


class JobRepository(BaseRepository[Job]):
    """Repository for Job operations in the MappingJobs table."""

    def __init__(
        self,
        table_name: Optional[str] = None,
        dynamodb_resource: Optional[Any] = None,
    ):
        """
        Initialize the job repository.

        Args:
            table_name: Optional table name override
            dynamodb_resource: Optional DynamoDB resource for testing
        """
        super().__init__(
            table_name=table_name or JOB_TABLE_NAME,
            model_class=Job,
            partition_key="job_id",
            sort_key=None,
            dynamodb_resource=dynamodb_resource,
        )

    def create_job(
        self,
        control_key: str,
        target_framework_key: str,
        target_control_ids: Optional[List[str]] = None,
    ) -> Job:
        """
        Create a new job record with idempotent insert.

        Uses conditional expression to prevent duplicate job creation.
        Since job_id is a UUID, duplicates should never occur, but the
        condition provides an extra safety layer.

        Args:
            control_key: Full source control key
            target_framework_key: Target framework key
            target_control_ids: Optional list of specific target control IDs

        Returns:
            Created Job instance
        """
        now = datetime.utcnow()
        ttl = int((now + timedelta(days=JOB_TTL_DAYS)).timestamp())

        job = Job(
            jobId=str(uuid.uuid4()),
            status=JobStatus.PENDING,
            controlKey=control_key,
            targetFrameworkKey=target_framework_key,
            createdAt=now.isoformat(),
            updatedAt=now.isoformat(),
            targetControlIds=target_control_ids,
            ttl=ttl,
        )

        # Use idempotent put to prevent duplicate job creation
        # Job uses to_dynamodb_item() which outputs snake_case keys
        self.table.put_item(
            Item=job.to_dynamodb_item(),
            ConditionExpression="attribute_not_exists(job_id)",
        )
        logger.info(f"Created job: {job.job_id}")

        return job


class AsyncMappingService:
    """Service class for async mapping job operations."""

    def __init__(
        self,
        dynamodb_resource: Optional[Any] = None,
        sqs_client: Optional[Any] = None,
        job_repository: Optional[JobRepository] = None,
        frameworks_table_name: Optional[str] = None,
        controls_table_name: Optional[str] = None,
        queue_url: Optional[str] = None,
    ):
        """
        Initialize the async mapping service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            sqs_client: Optional SQS client (for testing)
            job_repository: Optional JobRepository (for testing)
            frameworks_table_name: Optional frameworks table name override
            controls_table_name: Optional controls table name override
            queue_url: Optional SQS queue URL override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.sqs = sqs_client or boto3.client("sqs")
        self.job_repo = job_repository or JobRepository(dynamodb_resource=self.dynamodb)
        self.frameworks_table_name = frameworks_table_name or FRAMEWORKS_TABLE_NAME
        self.controls_table_name = controls_table_name or CONTROLS_TABLE_NAME
        self.queue_url = queue_url or MAPPING_REQUEST_QUEUE_URL

        self.frameworks_table = self.dynamodb.Table(self.frameworks_table_name)
        self.controls_table = self.dynamodb.Table(self.controls_table_name)

    # =========================================================================
    # Job Operations
    # =========================================================================

    def create_job(
        self,
        control_key: str,
        target_framework_key: str,
        target_control_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Create job record in DynamoDB using Job DAO.

        Args:
            control_key: Full source control key (e.g., "AWS.EC2#1.0#PR.1").
            target_framework_key: Target framework key (e.g., "NIST-800-53#R5").
            target_control_ids: Optional list of specific target control IDs.

        Returns:
            Generated job_id (UUID).
        """
        job = self.job_repo.create_job(
            control_key=control_key,
            target_framework_key=target_framework_key,
            target_control_ids=target_control_ids,
        )
        return job.job_id

    def enqueue_mapping_request(
        self,
        job_id: str,
        control_key: str,
        target_framework_key: str,
        target_control_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Enqueue mapping request to SQS for durable processing.

        The SQS Trigger Lambda will consume this message and start Step Functions.
        This provides durability - if Step Functions fails due to a bug requiring
        a code fix, the request is preserved in DLQ and can be retried after fix.

        Args:
            job_id: Job identifier.
            control_key: Full source control key.
            target_framework_key: Target framework key.
            target_control_ids: Optional list of specific target control IDs.

        Returns:
            SQS message ID.

        Raises:
            botocore.exceptions.ClientError: SQS send_message fails.
            ValueError: If queue URL is not configured.
        """
        if not self.queue_url:
            raise ValueError("MAPPING_REQUEST_QUEUE_URL environment variable is not set")

        message_body = {
            "job_id": job_id,
            "control_key": control_key,
            "target_framework_key": target_framework_key,
            "target_control_ids": target_control_ids,
        }

        # Handle FIFO vs standard queue
        send_params = {
            "QueueUrl": self.queue_url,
            "MessageBody": json.dumps(message_body),
        }

        if self.queue_url.endswith(".fifo"):
            send_params["MessageGroupId"] = control_key
            send_params["MessageDeduplicationId"] = job_id

        response = self.sqs.send_message(**send_params)
        message_id = response.get("MessageId", "")
        logger.info(f"Enqueued mapping request: job_id={job_id}, message_id={message_id}")

        return message_id

    # Keep old method name as alias for backward compatibility
    def start_workflow(
        self,
        job_id: str,
        control_key: str,
        target_framework_key: str,
        target_control_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Alias for enqueue_mapping_request for backward compatibility.

        Previously this method directly started Step Functions.
        Now it enqueues to SQS for durable processing.
        """
        return self.enqueue_mapping_request(
            job_id, control_key, target_framework_key, target_control_ids
        )

    # =========================================================================
    # Input Validation Functions
    # =========================================================================

    def validate_control_key_format(self, control_key: str) -> Optional[str]:
        """
        Validate control_key format.

        Args:
            control_key: Full control key to validate.

        Returns:
            Error message if invalid, None if valid.
        """
        if not control_key:
            return "control_key is required"
        if len(control_key) > MAX_CONTROL_KEY_LENGTH:
            return f"control_key exceeds maximum length of {MAX_CONTROL_KEY_LENGTH}"
        if not CONTROL_KEY_PATTERN.match(control_key):
            return (
                "control_key must match format: frameworkName#version#controlId "
                "(e.g., AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED)"
            )
        return None

    def validate_framework_key_format(self, framework_key: str) -> Optional[str]:
        """
        Validate target_framework_key format.

        Args:
            framework_key: Framework key to validate.

        Returns:
            Error message if invalid, None if valid.
        """
        if not framework_key:
            return "target_framework_key is required"
        if len(framework_key) > MAX_FRAMEWORK_KEY_LENGTH:
            return f"target_framework_key exceeds maximum length of {MAX_FRAMEWORK_KEY_LENGTH}"
        if not FRAMEWORK_KEY_PATTERN.match(framework_key):
            return (
                "target_framework_key must match format: frameworkName#version "
                "(e.g., NIST-SP-800-53#R5)"
            )
        return None

    def validate_target_control_ids(
        self, target_control_ids: List[Any]
    ) -> Optional[str]:
        """
        Validate target_control_ids is a list of strings.

        Args:
            target_control_ids: List to validate.

        Returns:
            Error message if invalid, None if valid.
        """
        if not isinstance(target_control_ids, list):
            return "target_control_ids must be a list"
        if len(target_control_ids) > MAX_CONTROL_IDS_COUNT:
            return f"target_control_ids exceeds maximum count of {MAX_CONTROL_IDS_COUNT}"
        for i, cid in enumerate(target_control_ids):
            if not isinstance(cid, str):
                return f"target_control_ids[{i}] must be a string"
            if not cid:
                return f"target_control_ids[{i}] cannot be empty"
        return None

    # =========================================================================
    # Database Validation Functions
    # =========================================================================

    def control_exists(self, control_key: str) -> Tuple[bool, Optional[str]]:
        """
        Check if control exists in FrameworkControls table.

        Args:
            control_key: Full control key to check.

        Returns:
            Tuple of (exists: bool, suggestion: Optional[str]).
        """
        # Query the ControlKeyIndex GSI
        result = self.controls_table.query(
            IndexName="ControlKeyIndex",
            KeyConditionExpression=Key("controlKey").eq(control_key),
            Limit=1,
        )
        if result.get("Items"):
            return True, None

        # Control not found - try to suggest similar controls
        parts = control_key.split("#")
        if len(parts) >= 2:
            framework_key = f"{parts[0]}#{parts[1]}"
            # Check if framework exists with any controls
            result = self.controls_table.query(
                KeyConditionExpression=Key("frameworkKey").eq(framework_key),
                Limit=3,
            )
            if result.get("Items"):
                sample_keys = [item["controlKey"] for item in result["Items"][:3]]
                return (
                    False,
                    f"Framework '{framework_key}' exists. Sample control keys: {sample_keys}",
                )

        return False, None

    def framework_exists(self, framework_key: str) -> Tuple[bool, List[str]]:
        """
        Check if framework exists in Frameworks table.

        Args:
            framework_key: Framework key (frameworkName#version).

        Returns:
            Tuple of (exists: bool, available_frameworks: list).
        """
        parts = framework_key.split("#")
        if len(parts) != 2:
            return False, []

        framework_name, version = parts

        # Check exact match
        result = self.frameworks_table.get_item(
            Key={"frameworkName": framework_name, "version": version}
        )
        if result.get("Item"):
            return True, []

        # Framework not found - list available versions for this framework name
        result = self.frameworks_table.query(
            KeyConditionExpression=Key("frameworkName").eq(framework_name),
        )
        if result.get("Items"):
            available = [
                f"{framework_name}#{item['version']}" for item in result["Items"]
            ]
            return False, available

        # Framework name not found - list all available frameworks
        result = self.frameworks_table.scan(Limit=20)
        available = [
            f"{item['frameworkName']}#{item['version']}"
            for item in result.get("Items", [])
        ]
        return False, available
