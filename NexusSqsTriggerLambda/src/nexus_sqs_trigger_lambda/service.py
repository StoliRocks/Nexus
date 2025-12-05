"""SQS Trigger Lambda Service.

Business logic for starting Step Functions workflows from SQS messages.
Uses DAOs from NexusApplicationInterface and response builders from NexusApplicationCommons.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from nexus_application_interface.api.v1 import Job
from nexus_application_interface.api.v1.models.enums import JobStatus
from nexus_application_commons.dynamodb.base_repository import BaseRepository

logger = logging.getLogger(__name__)

STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
JOB_TABLE_NAME = os.environ.get("JOB_TABLE_NAME", "MappingJobs")


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
            sort_key=None,  # Jobs table has no sort key
            dynamodb_resource=dynamodb_resource,
        )

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        condition_status: Optional[JobStatus] = None,
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status value
            condition_status: Optional - only update if current status matches

        Returns:
            True if update succeeded, False if condition failed
        """
        try:
            update_params = {
                "Key": {"job_id": job_id},
                "UpdateExpression": "SET #status = :status, updated_at = :updated_at",
                "ExpressionAttributeNames": {"#status": "status"},
                "ExpressionAttributeValues": {
                    ":status": status.value,
                    ":updated_at": datetime.utcnow().isoformat(),
                },
            }

            if condition_status:
                update_params["ConditionExpression"] = "#status = :condition_status"
                update_params["ExpressionAttributeValues"][":condition_status"] = (
                    condition_status.value
                )

            self.table.update_item(**update_params)
            logger.info(f"Updated job {job_id} status to {status.value}")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.info(
                    f"Job {job_id} status not updated - condition not met "
                    f"(expected {condition_status})"
                )
                return False
            logger.error(f"Failed to update job status for {job_id}: {e}")
            raise


class SqsTriggerService:
    """Service class for SQS trigger operations."""

    def __init__(
        self,
        sfn_client: Optional[Any] = None,
        job_repository: Optional[JobRepository] = None,
        state_machine_arn: Optional[str] = None,
    ):
        """
        Initialize the SQS trigger service.

        Args:
            sfn_client: Optional Step Functions client (for testing)
            job_repository: Optional JobRepository (for testing)
            state_machine_arn: Optional state machine ARN override
        """
        self.sfn = sfn_client or boto3.client("stepfunctions")
        self.job_repo = job_repository or JobRepository()
        self.state_machine_arn = state_machine_arn or STATE_MACHINE_ARN

    def start_workflow(
        self,
        job_id: str,
        control_key: str,
        target_framework_key: str,
        target_control_ids: Optional[list] = None,
    ) -> str:
        """
        Start Step Functions workflow for a mapping request.

        Args:
            job_id: Job identifier (used as execution name)
            control_key: Full source control key
            target_framework_key: Target framework key
            target_control_ids: Optional list of specific target control IDs

        Returns:
            Step Functions execution ARN

        Raises:
            botocore.exceptions.ClientError: If start_execution fails
            ValueError: If state machine ARN is not configured
        """
        if not self.state_machine_arn:
            raise ValueError("STATE_MACHINE_ARN environment variable is not set")

        sfn_input = {
            "job_id": job_id,
            "control_key": control_key,
            "target_framework_key": target_framework_key,
            "target_control_ids": target_control_ids,
        }

        logger.info(f"Starting Step Functions execution: {job_id}")

        try:
            response = self.sfn.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=job_id,
                input=json.dumps(sfn_input),
            )

            execution_arn = response["executionArn"]
            logger.info(f"Started execution: {execution_arn}")

            # Update job status to IN_PROGRESS
            self.job_repo.update_status(job_id, JobStatus.IN_PROGRESS)

            return execution_arn

        except self.sfn.exceptions.ExecutionAlreadyExists:
            # Execution already started (possibly from a retry)
            logger.warning(f"Execution already exists for job_id={job_id}")
            # Only update if still PENDING (idempotency)
            self.job_repo.update_status(
                job_id,
                JobStatus.IN_PROGRESS,
                condition_status=JobStatus.PENDING,
            )
            return f"arn:aws:states:::execution/{job_id}"

        except Exception as e:
            logger.error(f"Failed to start execution for job_id={job_id}: {e}")
            # Don't update job status here - let SQS retry handle it
            raise
