"""Tests for NexusControlAPIHandlerLambda module."""

import json
import os
import pytest
import boto3
from moto import mock_aws

from nexus_control_api_handler_lambda.handler import lambda_handler
from nexus_control_api_handler_lambda.service import ControlService
from nexus_application_interface.api.v1 import (
    ControlCreateRequest,
    BatchControlsCreateRequest,
    BatchArchiveRequest,
)


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
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlKey", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb


@pytest.fixture
def control_service(dynamodb_table):
    """Create a ControlService with mocked DynamoDB."""
    return ControlService(dynamodb_resource=dynamodb_table, table_name="FrameworkControls")


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    def test_missing_path_params(self):
        """Test that missing path params returns validation error."""
        event = {"httpMethod": "GET", "path": "/frameworks//controls", "pathParameters": {}}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    @mock_aws
    def test_invalid_json_body(self, aws_credentials):
        """Test that invalid JSON body returns validation error."""
        # Create mock table for ControlService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlKey", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "PUT",
            "path": "/frameworks/SOC2/v1/controls/CC1.1",
            "pathParameters": {
                "frameworkName": "SOC2",
                "frameworkVersion": "v1",
                "controlId": "CC1.1",
            },
            "body": "invalid json",
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    @mock_aws
    def test_method_not_allowed(self, aws_credentials):
        """Test that unsupported methods return 405."""
        # Create mock table for ControlService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="FrameworkControls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlKey", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "DELETE",
            "path": "/frameworks/SOC2/v1/controls",
            "pathParameters": {"frameworkName": "SOC2", "frameworkVersion": "v1"},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 405


class TestControlService:
    """Tests for ControlService class."""

    def test_list_controls_empty(self, control_service):
        """Test listing controls when none exist."""
        response = control_service.list_controls("SOC2#v1", {})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["controls"] == []
        assert body["count"] == 0

    def test_create_control(self, control_service):
        """Test creating a new control."""
        request = ControlCreateRequest(title="Security Policy", description="Test control")
        response = control_service.create_or_update_control(
            "SOC2#v1",
            "CC1.1",
            request,
        )
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["controlId"] == "CC1.1"
        assert body["title"] == "Security Policy"

    def test_create_control_missing_title(self, control_service):
        """Test that creating a control without title fails validation."""
        # Pydantic will raise ValidationError when title is missing
        with pytest.raises(Exception):
            ControlCreateRequest(description="No title")

    def test_get_control(self, control_service):
        """Test getting a control."""
        # First create
        request = ControlCreateRequest(title="Security Policy")
        control_service.create_or_update_control("SOC2#v1", "CC1.1", request)
        # Then get
        response = control_service.get_control("SOC2#v1", "CC1.1")
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["controlId"] == "CC1.1"

    def test_get_control_not_found(self, control_service):
        """Test getting a non-existent control."""
        response = control_service.get_control("SOC2#v1", "NOTFOUND")
        assert response["statusCode"] == 404

    def test_update_control(self, control_service):
        """Test updating an existing control."""
        # Create
        request = ControlCreateRequest(title="Original Title")
        control_service.create_or_update_control("SOC2#v1", "CC1.1", request)
        # Update
        update_request = ControlCreateRequest(title="Updated Title")
        response = control_service.create_or_update_control(
            "SOC2#v1", "CC1.1", update_request
        )
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["title"] == "Updated Title"

    def test_archive_control(self, control_service):
        """Test archiving a control."""
        # Create
        request = ControlCreateRequest(title="To Archive")
        control_service.create_or_update_control("SOC2#v1", "CC1.1", request)
        # Archive
        response = control_service.archive_control("SOC2#v1", "CC1.1")
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ARCHIVED"

    def test_archive_control_not_found(self, control_service):
        """Test archiving a non-existent control."""
        response = control_service.archive_control("SOC2#v1", "NOTFOUND")
        assert response["statusCode"] == 404

    def test_archive_already_archived(self, control_service):
        """Test archiving an already archived control."""
        # Create and archive
        request = ControlCreateRequest(title="To Archive")
        control_service.create_or_update_control("SOC2#v1", "CC1.1", request)
        control_service.archive_control("SOC2#v1", "CC1.1")
        # Try to archive again
        response = control_service.archive_control("SOC2#v1", "CC1.1")
        assert response["statusCode"] == 400

    def test_batch_create_controls(self, control_service):
        """Test batch creating controls."""
        request = BatchControlsCreateRequest(
            controls=[
                {"controlId": "CC1.1", "title": "Control 1"},
                {"controlId": "CC1.2", "title": "Control 2"},
            ]
        )
        response = control_service.batch_create_controls("SOC2#v1", request)
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["createdCount"] == 2

    def test_batch_create_empty(self, control_service):
        """Test batch create with empty list raises validation error."""
        # Pydantic will raise ValidationError when controls list is empty
        with pytest.raises(Exception):
            BatchControlsCreateRequest(controls=[])

    def test_batch_archive_controls(self, control_service):
        """Test batch archiving controls."""
        # Create controls first
        create_request = BatchControlsCreateRequest(
            controls=[
                {"controlId": "CC1.1", "title": "Control 1"},
                {"controlId": "CC1.2", "title": "Control 2"},
            ]
        )
        control_service.batch_create_controls("SOC2#v1", create_request)
        # Batch archive
        archive_request = BatchArchiveRequest(control_ids=["CC1.1", "CC1.2"])
        response = control_service.batch_archive_controls("SOC2#v1", archive_request)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["archivedCount"] == 2

    def test_list_controls_with_status_filter(self, control_service):
        """Test listing controls with status filter."""
        # Create controls
        request1 = ControlCreateRequest(title="Active")
        control_service.create_or_update_control("SOC2#v1", "CC1.1", request1)
        request2 = ControlCreateRequest(title="Another Active")
        control_service.create_or_update_control("SOC2#v1", "CC1.2", request2)
        # Archive one
        control_service.archive_control("SOC2#v1", "CC1.2")
        # List with filter
        response = control_service.list_controls("SOC2#v1", {"status": "ACTIVE"})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["controls"][0]["status"] == "ACTIVE"
