"""Async handler business logic.

Supports Nexus Database Schema:
- control_key: Full control key (frameworkKey#controlId)
- target_framework_key: Full target framework key (frameworkName#version)
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

logger = logging.getLogger(__name__)

JOB_TABLE_NAME = os.environ.get("JOB_TABLE_NAME", "MappingJobs")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
FRAMEWORKS_TABLE_NAME = os.environ.get("FRAMEWORKS_TABLE_NAME", "Frameworks")
CONTROLS_TABLE_NAME = os.environ.get("CONTROLS_TABLE_NAME", "FrameworkControls")
JOB_TTL_DAYS = 7

# Validation constants
MAX_CONTROL_KEY_LENGTH = 256
MAX_FRAMEWORK_KEY_LENGTH = 128
MAX_CONTROL_IDS_COUNT = 100
CONTROL_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+#.+$")
FRAMEWORK_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+$")


class AsyncMappingService:
    """Service class for async mapping job operations."""

    def __init__(
        self,
        dynamodb_resource: Optional[Any] = None,
        sfn_client: Optional[Any] = None,
        job_table_name: Optional[str] = None,
        frameworks_table_name: Optional[str] = None,
        controls_table_name: Optional[str] = None,
        state_machine_arn: Optional[str] = None,
    ):
        """
        Initialize the async mapping service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            sfn_client: Optional Step Functions client (for testing)
            job_table_name: Optional job table name override
            frameworks_table_name: Optional frameworks table name override
            controls_table_name: Optional controls table name override
            state_machine_arn: Optional state machine ARN override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.sfn = sfn_client or boto3.client("stepfunctions")
        self.job_table_name = job_table_name or JOB_TABLE_NAME
        self.frameworks_table_name = frameworks_table_name or FRAMEWORKS_TABLE_NAME
        self.controls_table_name = controls_table_name or CONTROLS_TABLE_NAME
        self.state_machine_arn = state_machine_arn or STATE_MACHINE_ARN

        self.job_table = self.dynamodb.Table(self.job_table_name)
        self.frameworks_table = self.dynamodb.Table(self.frameworks_table_name)
        self.controls_table = self.dynamodb.Table(self.controls_table_name)

    # =========================================================================
    # Job Operations
    # =========================================================================

    def create_job(
        self,
        control_key: str,
        target_framework_key: str,
        target_control_ids: Optional[List[str]],
    ) -> str:
        """
        Create job record in DynamoDB.

        Args:
            control_key: Full source control key (e.g., "AWS.EC2#1.0#PR.1").
            target_framework_key: Target framework key (e.g., "NIST-800-53#R5").
            target_control_ids: Optional list of specific target control IDs.

        Returns:
            Generated job_id (UUID).
        """
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        ttl = int((now + timedelta(days=JOB_TTL_DAYS)).timestamp())

        item = {
            "job_id": job_id,
            "status": "PENDING",
            "control_key": control_key,
            "target_framework_key": target_framework_key,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "ttl": ttl,
        }

        if target_control_ids:
            item["target_control_ids"] = target_control_ids

        self.job_table.put_item(Item=item)
        return job_id

    def start_workflow(
        self,
        job_id: str,
        control_key: str,
        target_framework_key: str,
        target_control_ids: Optional[List[str]],
    ) -> None:
        """
        Start Step Functions workflow and update job status to RUNNING.

        Args:
            job_id: Job identifier.
            control_key: Full source control key.
            target_framework_key: Target framework key.
            target_control_ids: Optional list of specific target control IDs.

        Raises:
            botocore.exceptions.ClientError: Step Functions start_execution fails.
        """
        sfn_input = {
            "job_id": job_id,
            "control_key": control_key,
            "target_framework_key": target_framework_key,
            "target_control_ids": target_control_ids,
        }
        self.sfn.start_execution(
            stateMachineArn=self.state_machine_arn,
            name=job_id,
            input=json.dumps(sfn_input),
        )

        self.job_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #status = :status, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "RUNNING",
                ":updated_at": datetime.utcnow().isoformat(),
            },
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

    def validate_target_control_ids(self, target_control_ids: list) -> Optional[str]:
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
                return False, f"Framework '{framework_key}' exists. Sample control keys: {sample_keys}"

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
