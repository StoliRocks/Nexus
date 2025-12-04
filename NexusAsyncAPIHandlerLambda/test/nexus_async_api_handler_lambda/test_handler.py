"""Tests for NexusAsyncAPIHandlerLambda handler."""

import json
import os
import pytest
import boto3
from moto import mock_aws
from unittest.mock import MagicMock, patch

from nexus_async_api_handler_lambda.handler import lambda_handler
from nexus_async_api_handler_lambda.service import AsyncMappingService


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["JOB_TABLE_NAME"] = "MappingJobs"
    os.environ["STATE_MACHINE_ARN"] = "arn:aws:states:us-east-1:123456789012:stateMachine:test"
    os.environ["FRAMEWORKS_TABLE_NAME"] = "Frameworks"
    os.environ["CONTROLS_TABLE_NAME"] = "FrameworkControls"


@pytest.fixture
def dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create Jobs table
        jobs_table = dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        jobs_table.wait_until_exists()

        # Create Frameworks table
        frameworks_table = dynamodb.create_table(
            TableName="Frameworks",
            KeySchema=[
                {"AttributeName": "frameworkName", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkName", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        frameworks_table.wait_until_exists()

        # Create Controls table with GSI
        controls_table = dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlId", "AttributeType": "S"},
                {"AttributeName": "controlKey", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "ControlKeyIndex",
                    "KeySchema": [{"AttributeName": "controlKey", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        controls_table.wait_until_exists()

        yield dynamodb


@pytest.fixture
def populated_tables(dynamodb_tables):
    """Populate tables with test data."""
    # Add a framework
    frameworks_table = dynamodb_tables.Table("Frameworks")
    frameworks_table.put_item(
        Item={
            "frameworkName": "NIST-SP-800-53",
            "version": "R5",
            "displayName": "NIST SP 800-53 Rev 5",
            "status": "ACTIVE",
        }
    )

    # Add a control
    controls_table = dynamodb_tables.Table("FrameworkControls")
    controls_table.put_item(
        Item={
            "frameworkKey": "AWS.ControlCatalog#1.0",
            "controlId": "API_GW_CACHE_ENABLED",
            "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "title": "API Gateway Cache Enabled",
            "status": "ACTIVE",
        }
    )

    return dynamodb_tables


@pytest.fixture
def mock_sfn_client():
    """Create a mock Step Functions client."""
    mock_client = MagicMock()
    mock_client.start_execution.return_value = {
        "executionArn": "arn:aws:states:us-east-1:123456789012:execution:test:test-id",
        "startDate": "2024-01-01T00:00:00Z",
    }
    return mock_client


@pytest.fixture
def service(populated_tables, mock_sfn_client):
    """Create an AsyncMappingService with mocked dependencies."""
    return AsyncMappingService(
        dynamodb_resource=populated_tables,
        sfn_client=mock_sfn_client,
        job_table_name="MappingJobs",
        frameworks_table_name="Frameworks",
        controls_table_name="FrameworkControls",
        state_machine_arn="arn:aws:states:us-east-1:123456789012:stateMachine:test",
    )


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    @mock_aws
    def test_invalid_json_body(self, aws_credentials):
        """Test that invalid JSON body returns validation error."""
        # Create mock tables for AsyncMappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="Frameworks",
            KeySchema=[
                {"AttributeName": "frameworkName", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkName", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {"httpMethod": "POST", "body": "invalid json"}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Invalid JSON body" in body["error"]["message"]

    @mock_aws
    def test_missing_control_key(self, aws_credentials):
        """Test that missing control_key returns validation error."""
        # Create mock tables for AsyncMappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="Frameworks",
            KeySchema=[
                {"AttributeName": "frameworkName", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkName", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "POST",
            "body": json.dumps({"target_framework_key": "NIST-SP-800-53#R5"}),
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "control_key is required" in body["error"]["message"]

    @mock_aws
    def test_missing_framework_key(self, aws_credentials):
        """Test that missing target_framework_key returns validation error."""
        # Create mock tables for AsyncMappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="Frameworks",
            KeySchema=[
                {"AttributeName": "frameworkName", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkName", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {"control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"}
            ),
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "target_framework_key is required" in body["error"]["message"]

    @mock_aws
    def test_invalid_control_key_format(self, aws_credentials):
        """Test that invalid control_key format returns validation error."""
        # Create mock tables for AsyncMappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="Frameworks",
            KeySchema=[
                {"AttributeName": "frameworkName", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkName", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "control_key": "invalid-format",
                    "target_framework_key": "NIST-SP-800-53#R5",
                }
            ),
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "control_key must match format" in body["error"]["message"]

    @mock_aws
    def test_invalid_framework_key_format(self, aws_credentials):
        """Test that invalid framework_key format returns validation error."""
        # Create mock tables for AsyncMappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="Frameworks",
            KeySchema=[
                {"AttributeName": "frameworkName", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkName", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
                    "target_framework_key": "invalid-format",
                }
            ),
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "target_framework_key must match format" in body["error"]["message"]

    @mock_aws
    def test_camelcase_field_names_accepted(self, aws_credentials):
        """Test that camelCase field names are accepted."""
        # Create mock tables for AsyncMappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingJobs",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="Frameworks",
            KeySchema=[
                {"AttributeName": "frameworkName", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkName", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
                    "targetFrameworkKey": "NIST-SP-800-53#R5",
                }
            ),
        }
        # Will fail on database validation, but format validation should pass
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        # Should fail at database validation, not format validation
        assert "not found in database" in body["error"]["message"]


class TestAsyncMappingService:
    """Tests for AsyncMappingService class."""

    def test_validate_control_key_format_valid(self, service):
        """Test valid control_key format passes validation."""
        result = service.validate_control_key_format(
            "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
        )
        assert result is None

    def test_validate_control_key_format_invalid(self, service):
        """Test invalid control_key format returns error."""
        result = service.validate_control_key_format("invalid-format")
        assert result is not None
        assert "control_key must match format" in result

    def test_validate_control_key_format_empty(self, service):
        """Test empty control_key returns error."""
        result = service.validate_control_key_format("")
        assert result is not None
        assert "control_key is required" in result

    def test_validate_control_key_format_too_long(self, service):
        """Test control_key exceeding max length returns error."""
        long_key = "A" * 300
        result = service.validate_control_key_format(long_key)
        assert result is not None
        assert "exceeds maximum length" in result

    def test_validate_framework_key_format_valid(self, service):
        """Test valid framework_key format passes validation."""
        result = service.validate_framework_key_format("NIST-SP-800-53#R5")
        assert result is None

    def test_validate_framework_key_format_invalid(self, service):
        """Test invalid framework_key format returns error."""
        result = service.validate_framework_key_format("invalid-format")
        assert result is not None
        assert "target_framework_key must match format" in result

    def test_validate_target_control_ids_valid(self, service):
        """Test valid target_control_ids passes validation."""
        result = service.validate_target_control_ids(["AC-1", "AC-2", "AC-3"])
        assert result is None

    def test_validate_target_control_ids_not_list(self, service):
        """Test non-list target_control_ids returns error."""
        result = service.validate_target_control_ids("AC-1")
        assert result is not None
        assert "must be a list" in result

    def test_validate_target_control_ids_too_many(self, service):
        """Test target_control_ids exceeding max count returns error."""
        result = service.validate_target_control_ids([f"AC-{i}" for i in range(150)])
        assert result is not None
        assert "exceeds maximum count" in result

    def test_validate_target_control_ids_non_string(self, service):
        """Test non-string item in target_control_ids returns error."""
        result = service.validate_target_control_ids(["AC-1", 123, "AC-3"])
        assert result is not None
        assert "must be a string" in result

    def test_validate_target_control_ids_empty_string(self, service):
        """Test empty string in target_control_ids returns error."""
        result = service.validate_target_control_ids(["AC-1", "", "AC-3"])
        assert result is not None
        assert "cannot be empty" in result

    def test_control_exists_found(self, service):
        """Test control_exists returns True when control exists."""
        exists, suggestion = service.control_exists(
            "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
        )
        assert exists is True
        assert suggestion is None

    def test_control_exists_not_found(self, service):
        """Test control_exists returns False when control doesn't exist."""
        exists, suggestion = service.control_exists(
            "AWS.ControlCatalog#1.0#NONEXISTENT"
        )
        assert exists is False

    def test_framework_exists_found(self, service):
        """Test framework_exists returns True when framework exists."""
        exists, available = service.framework_exists("NIST-SP-800-53#R5")
        assert exists is True
        assert available == []

    def test_framework_exists_not_found(self, service):
        """Test framework_exists returns False when framework doesn't exist."""
        exists, available = service.framework_exists("NONEXISTENT#v1")
        assert exists is False

    def test_create_job(self, service):
        """Test create_job creates a job record."""
        job_id = service.create_job(
            control_key="AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            target_framework_key="NIST-SP-800-53#R5",
            target_control_ids=["AC-1", "AC-2"],
        )
        assert job_id is not None

        # Verify job was created in DynamoDB
        job_table = service.job_table
        result = job_table.get_item(Key={"job_id": job_id})
        item = result.get("Item")
        assert item is not None
        assert item["status"] == "PENDING"
        assert item["control_key"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
        assert item["target_framework_key"] == "NIST-SP-800-53#R5"
        assert item["target_control_ids"] == ["AC-1", "AC-2"]

    def test_create_job_without_target_control_ids(self, service):
        """Test create_job works without target_control_ids."""
        job_id = service.create_job(
            control_key="AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            target_framework_key="NIST-SP-800-53#R5",
            target_control_ids=None,
        )

        job_table = service.job_table
        result = job_table.get_item(Key={"job_id": job_id})
        item = result.get("Item")
        assert "target_control_ids" not in item

    def test_start_workflow(self, service, mock_sfn_client):
        """Test start_workflow starts Step Functions and updates job status."""
        # First create a job
        job_id = service.create_job(
            control_key="AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            target_framework_key="NIST-SP-800-53#R5",
            target_control_ids=None,
        )

        # Start workflow
        service.start_workflow(
            job_id=job_id,
            control_key="AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            target_framework_key="NIST-SP-800-53#R5",
            target_control_ids=None,
        )

        # Verify Step Functions was called
        mock_sfn_client.start_execution.assert_called_once()
        call_args = mock_sfn_client.start_execution.call_args
        assert call_args.kwargs["name"] == job_id

        # Verify job status was updated to RUNNING
        job_table = service.job_table
        result = job_table.get_item(Key={"job_id": job_id})
        item = result.get("Item")
        assert item["status"] == "RUNNING"


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_successful_mapping_request(self, populated_tables, mock_sfn_client):
        """Test successful POST /mappings request."""
        with patch(
            "nexus_async_api_handler_lambda.service.boto3.resource"
        ) as mock_resource, patch(
            "nexus_async_api_handler_lambda.service.boto3.client"
        ) as mock_client:
            mock_resource.return_value = populated_tables
            mock_client.return_value = mock_sfn_client

            event = {
                "httpMethod": "POST",
                "body": json.dumps(
                    {
                        "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
                        "target_framework_key": "NIST-SP-800-53#R5",
                    }
                ),
                "requestContext": {
                    "domainName": "api.example.com",
                    "stage": "prod",
                },
            }

            response = lambda_handler(event, None)
            assert response["statusCode"] == 202

            body = json.loads(response["body"])
            assert "mappingId" in body
            assert body["status"] == "ACCEPTED"
            assert "statusUrl" in body
            assert body["controlKey"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
            assert body["targetFrameworkKey"] == "NIST-SP-800-53#R5"
