"""Tests for NexusStatusAPIHandlerLambda handler."""

import json
import os
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch

from nexus_status_api_handler_lambda.handler import lambda_handler
from nexus_status_api_handler_lambda.service import StatusService


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["JOB_TABLE_NAME"] = "MappingJobs"


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
    """Populate table with test data."""
    table = dynamodb_table.Table("MappingJobs")

    # Pending job
    table.put_item(
        Item={
            "job_id": "pending-job-id",
            "status": "PENDING",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework_key": "NIST-SP-800-53#R5",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }
    )

    # Running job
    table.put_item(
        Item={
            "job_id": "running-job-id",
            "status": "RUNNING",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework_key": "NIST-SP-800-53#R5",
            "target_control_ids": ["AC-1", "AC-2"],
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:01:00Z",
        }
    )

    # Completed job
    table.put_item(
        Item={
            "job_id": "completed-job-id",
            "status": "COMPLETED",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework_key": "NIST-SP-800-53#R5",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:05:00Z",
            "mappings": [
                {
                    "targetControlKey": "NIST-SP-800-53#R5#AC-1",
                    "similarityScore": 0.92,
                    "rerankScore": 0.95,
                }
            ],
            "reasoning": {
                "NIST-SP-800-53#R5#AC-1": "Both controls address access management."
            },
        }
    )

    # Failed job
    table.put_item(
        Item={
            "job_id": "failed-job-id",
            "status": "FAILED",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework_key": "NIST-SP-800-53#R5",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:02:00Z",
            "error_message": "Enrichment service unavailable",
        }
    )

    return dynamodb_table


@pytest.fixture
def service(populated_table):
    """Create a StatusService with mocked DynamoDB."""
    return StatusService(dynamodb_resource=populated_table, table_name="MappingJobs")


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    @mock_aws
    def test_missing_mapping_id(self, aws_credentials):
        """Test that missing mappingId returns validation error."""
        # Create mock table for StatusService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {"pathParameters": {}}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "mappingId is required" in body["error"]["message"]

    @mock_aws
    def test_null_path_parameters(self, aws_credentials):
        """Test that null pathParameters returns validation error."""
        # Create mock table for StatusService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {"pathParameters": None}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "mappingId is required" in body["error"]["message"]

    @mock_aws
    def test_missing_path_parameters_key(self, aws_credentials):
        """Test that missing pathParameters key returns validation error."""
        # Create mock table for StatusService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "mappingId is required" in body["error"]["message"]


class TestStatusService:
    """Tests for StatusService class."""

    def test_get_pending_job(self, service):
        """Test getting a pending job."""
        response = service.get_job_status("pending-job-id")
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["mappingId"] == "pending-job-id"
        assert body["status"] == "PENDING"
        assert body["controlKey"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
        assert body["targetFrameworkKey"] == "NIST-SP-800-53#R5"
        assert "result" not in body
        assert "error" not in body

    def test_get_running_job(self, service):
        """Test getting a running job with target_control_ids."""
        response = service.get_job_status("running-job-id")
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["mappingId"] == "running-job-id"
        assert body["status"] == "RUNNING"
        assert body["targetControlIds"] == ["AC-1", "AC-2"]

    def test_get_completed_job(self, service):
        """Test getting a completed job with results."""
        response = service.get_job_status("completed-job-id")
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["mappingId"] == "completed-job-id"
        assert body["status"] == "COMPLETED"
        assert "result" in body
        assert "mappings" in body["result"]
        assert len(body["result"]["mappings"]) == 1
        assert body["result"]["mappings"][0]["targetControlKey"] == "NIST-SP-800-53#R5#AC-1"
        assert "reasoning" in body["result"]

    def test_get_failed_job(self, service):
        """Test getting a failed job with error."""
        response = service.get_job_status("failed-job-id")
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["mappingId"] == "failed-job-id"
        assert body["status"] == "FAILED"
        assert body["error"] == "Enrichment service unavailable"
        assert "result" not in body

    def test_get_nonexistent_job(self, service):
        """Test getting a job that doesn't exist."""
        response = service.get_job_status("nonexistent-job-id")
        assert response["statusCode"] == 404

        body = json.loads(response["body"])
        assert "not found" in body["error"]["message"].lower()


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_successful_status_query(self, populated_table):
        """Test successful GET /mappings/{mappingId} request."""
        with patch(
            "nexus_status_api_handler_lambda.service.boto3.resource"
        ) as mock_resource:
            mock_resource.return_value = populated_table

            event = {
                "pathParameters": {"mappingId": "completed-job-id"},
            }

            response = lambda_handler(event, None)
            assert response["statusCode"] == 200

            body = json.loads(response["body"])
            assert body["mappingId"] == "completed-job-id"
            assert body["status"] == "COMPLETED"
            assert "result" in body

    def test_job_not_found(self, populated_table):
        """Test GET request for nonexistent job."""
        with patch(
            "nexus_status_api_handler_lambda.service.boto3.resource"
        ) as mock_resource:
            mock_resource.return_value = populated_table

            event = {
                "pathParameters": {"mappingId": "nonexistent-id"},
            }

            response = lambda_handler(event, None)
            assert response["statusCode"] == 404
