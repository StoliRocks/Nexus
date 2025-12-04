"""Tests for NexusJobUpdaterLambda handler."""

import os
import pytest
import boto3
from moto import mock_aws
from decimal import Decimal

from nexus_job_updater_lambda.handler import lambda_handler
from nexus_job_updater_lambda.service import JobUpdaterService


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb


@pytest.fixture
def populated_table(dynamodb_table):
    """Populate table with test jobs."""
    table = dynamodb_table.Table("MappingJobs")

    # Running job
    table.put_item(
        Item={
            "job_id": "running-job-id",
            "status": "RUNNING",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework_key": "NIST-SP-800-53#R5",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:01:00Z",
        }
    )

    return dynamodb_table


@pytest.fixture
def service(populated_table):
    """Create a JobUpdaterService with mocked DynamoDB."""
    return JobUpdaterService(
        dynamodb_resource=populated_table,
        job_table_name="MappingJobs",
    )


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    def test_missing_job_id(self):
        """Test that missing job_id raises ValueError."""
        event = {"status": "COMPLETED"}
        with pytest.raises(ValueError, match="job_id is required"):
            lambda_handler(event, None)

    def test_missing_status(self):
        """Test that missing status raises ValueError."""
        event = {"job_id": "test-job-id"}
        with pytest.raises(ValueError, match="status is required"):
            lambda_handler(event, None)

    def test_unknown_status(self):
        """Test that unknown status raises ValueError."""
        event = {"job_id": "test-job-id", "status": "UNKNOWN"}
        with pytest.raises(ValueError, match="Unknown status"):
            lambda_handler(event, None)


class TestUpdateJobCompleted:
    """Tests for update_job_completed method."""

    def test_update_completed_with_mappings(self, service, populated_table):
        """Test updating job with successful mappings."""
        mappings = [
            {
                "target_control_id": "NIST-SP-800-53#R5#AC-1",
                "target_framework": "NIST-SP-800-53",
                "similarity_score": 0.87,
                "rerank_score": 0.92,
            },
            {
                "target_control_id": "NIST-SP-800-53#R5#AC-2",
                "target_framework": "NIST-SP-800-53",
                "similarity_score": 0.75,
                "rerank_score": 0.80,
            },
        ]
        reasoning = [
            {
                "control_id": "NIST-SP-800-53#R5#AC-1",
                "reasoning": "Both controls address access management.",
            },
            {
                "control_id": "NIST-SP-800-53#R5#AC-2",
                "reasoning": "Both controls address authorization.",
            },
        ]

        result = service.update_job_completed(
            job_id="running-job-id",
            mappings=mappings,
            reasoning_results=reasoning,
        )

        assert result["job_id"] == "running-job-id"
        assert result["status"] == "COMPLETED"
        assert result["mapping_count"] == 2

        # Verify DynamoDB record
        table = populated_table.Table("MappingJobs")
        response = table.get_item(Key={"job_id": "running-job-id"})
        item = response["Item"]

        assert item["status"] == "COMPLETED"
        assert "completed_at" in item
        assert len(item["mappings"]) == 2
        assert item["mappings"][0]["reasoning"] == "Both controls address access management."

    def test_update_completed_merges_reasoning(self, service, populated_table):
        """Test that reasoning is properly merged with mappings."""
        mappings = [
            {"target_control_id": "AC-1", "similarity_score": 0.9},
            {"target_control_id": "AC-2", "similarity_score": 0.8},
            {"target_control_id": "AC-3", "similarity_score": 0.7},
        ]
        reasoning = [
            {"control_id": "AC-1", "reasoning": "Reasoning for AC-1"},
            {"control_id": "AC-3", "reasoning": "Reasoning for AC-3"},
            # AC-2 has no reasoning
        ]

        result = service.update_job_completed(
            job_id="running-job-id",
            mappings=mappings,
            reasoning_results=reasoning,
        )

        table = populated_table.Table("MappingJobs")
        response = table.get_item(Key={"job_id": "running-job-id"})
        item = response["Item"]

        # Find mappings by target_control_id
        mapping_dict = {m["target_control_id"]: m for m in item["mappings"]}
        assert mapping_dict["AC-1"]["reasoning"] == "Reasoning for AC-1"
        assert mapping_dict["AC-2"]["reasoning"] == ""  # No reasoning provided
        assert mapping_dict["AC-3"]["reasoning"] == "Reasoning for AC-3"

    def test_update_completed_empty_mappings(self, service, populated_table):
        """Test updating job with empty mappings."""
        result = service.update_job_completed(
            job_id="running-job-id",
            mappings=[],
            reasoning_results=[],
        )

        assert result["mapping_count"] == 0
        assert result["status"] == "COMPLETED"

    def test_update_completed_with_target_control_key(self, service, populated_table):
        """Test that target_control_key is used when target_control_id is missing."""
        mappings = [
            {
                "target_control_key": "NIST#R5#AC-1",
                "target_framework_key": "NIST#R5",
                "similarity_score": 0.85,
            }
        ]
        reasoning = [
            {"control_id": "NIST#R5#AC-1", "reasoning": "Test reasoning"}
        ]

        result = service.update_job_completed(
            job_id="running-job-id",
            mappings=mappings,
            reasoning_results=reasoning,
        )

        table = populated_table.Table("MappingJobs")
        response = table.get_item(Key={"job_id": "running-job-id"})
        item = response["Item"]

        assert item["mappings"][0]["target_control_key"] == "NIST#R5#AC-1"
        assert item["mappings"][0]["reasoning"] == "Test reasoning"


class TestUpdateJobFailed:
    """Tests for update_job_failed method."""

    def test_update_failed_with_dict_error(self, service, populated_table):
        """Test updating job with error dict from Step Functions."""
        error = {
            "Error": "EnrichmentError",
            "Cause": "NexusStrandsAgentService unavailable",
        }

        result = service.update_job_failed(
            job_id="running-job-id",
            error=error,
        )

        assert result["job_id"] == "running-job-id"
        assert result["status"] == "FAILED"
        assert result["error"] == "NexusStrandsAgentService unavailable"

        # Verify DynamoDB record
        table = populated_table.Table("MappingJobs")
        response = table.get_item(Key={"job_id": "running-job-id"})
        item = response["Item"]

        assert item["status"] == "FAILED"
        assert "failed_at" in item
        assert item["error_message"] == "NexusStrandsAgentService unavailable"

    def test_update_failed_with_string_error(self, service, populated_table):
        """Test updating job with string error."""
        result = service.update_job_failed(
            job_id="running-job-id",
            error="Simple error message",
        )

        assert result["error"] == "Simple error message"

        table = populated_table.Table("MappingJobs")
        response = table.get_item(Key={"job_id": "running-job-id"})
        item = response["Item"]

        assert item["error_message"] == "Simple error message"

    def test_update_failed_with_message_key(self, service, populated_table):
        """Test updating job with error dict containing 'message' key."""
        error = {"message": "Error with message key"}

        result = service.update_job_failed(
            job_id="running-job-id",
            error=error,
        )

        assert result["error"] == "Error with message key"

    def test_update_failed_with_empty_dict(self, service, populated_table):
        """Test updating job with empty error dict."""
        result = service.update_job_failed(
            job_id="running-job-id",
            error={},
        )

        # Should convert empty dict to string
        assert result["error"] == "{}"


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_completed_workflow(self, populated_table):
        """Test complete successful workflow update."""
        from unittest.mock import patch

        with patch(
            "nexus_job_updater_lambda.handler.JobUpdaterService"
        ) as MockService:
            mock_service = JobUpdaterService(
                dynamodb_resource=populated_table,
                job_table_name="MappingJobs",
            )
            MockService.return_value = mock_service

            event = {
                "job_id": "running-job-id",
                "status": "COMPLETED",
                "mappings": [
                    {
                        "target_control_id": "AC-1",
                        "similarity_score": 0.9,
                        "rerank_score": 0.95,
                    }
                ],
                "reasoning": [
                    {"control_id": "AC-1", "reasoning": "Test reasoning"}
                ],
            }

            response = lambda_handler(event, None)

            assert response["status"] == "COMPLETED"
            assert response["mapping_count"] == 1

    def test_failed_workflow(self, populated_table):
        """Test complete failed workflow update."""
        from unittest.mock import patch

        with patch(
            "nexus_job_updater_lambda.handler.JobUpdaterService"
        ) as MockService:
            mock_service = JobUpdaterService(
                dynamodb_resource=populated_table,
                job_table_name="MappingJobs",
            )
            MockService.return_value = mock_service

            event = {
                "job_id": "running-job-id",
                "status": "FAILED",
                "error": {"Cause": "Service timeout"},
            }

            response = lambda_handler(event, None)

            assert response["status"] == "FAILED"
            assert response["error"] == "Service timeout"
