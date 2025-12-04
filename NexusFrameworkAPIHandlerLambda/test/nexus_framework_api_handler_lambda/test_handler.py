"""Tests for NexusFrameworkAPIHandlerLambda module."""

import json
import os
import pytest
import boto3
from moto import mock_aws

from nexus_framework_api_handler_lambda.handler import lambda_handler
from nexus_framework_api_handler_lambda.service import FrameworkService


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
        table.wait_until_exists()
        yield dynamodb


@pytest.fixture
def framework_service(dynamodb_table):
    """Create a FrameworkService with mocked DynamoDB."""
    return FrameworkService(dynamodb_resource=dynamodb_table, table_name="Frameworks")


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    @mock_aws
    def test_invalid_json_body(self, aws_credentials):
        """Test that invalid JSON body returns validation error."""
        # Create mock table for FrameworkService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
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

        event = {
            "httpMethod": "PUT",
            "path": "/frameworks/SOC2/v1",
            "pathParameters": {
                "frameworkName": "SOC2",
                "frameworkVersion": "v1",
            },
            "body": "invalid json",
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    @mock_aws
    def test_method_not_allowed(self, aws_credentials):
        """Test that unsupported methods return 405."""
        # Create mock table for FrameworkService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
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

        event = {
            "httpMethod": "DELETE",
            "path": "/frameworks/SOC2/v1",
            "pathParameters": {"frameworkName": "SOC2", "frameworkVersion": "v1"},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 405


class TestFrameworkService:
    """Tests for FrameworkService class."""

    def test_list_frameworks_empty(self, framework_service):
        """Test listing frameworks when none exist."""
        response = framework_service.list_frameworks({})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["frameworks"] == []
        assert body["count"] == 0

    def test_create_framework(self, framework_service):
        """Test creating a new framework."""
        response = framework_service.create_or_update_framework(
            "SOC2",
            "v1",
            {"description": "SOC 2 Type II Framework", "source": "AICPA"},
        )
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["frameworkName"] == "SOC2"
        assert body["version"] == "v1"
        assert body["frameworkKey"] == "SOC2#v1"

    def test_get_framework(self, framework_service):
        """Test getting a framework."""
        # First create
        framework_service.create_or_update_framework(
            "SOC2", "v1", {"description": "SOC 2"}
        )
        # Then get
        response = framework_service.get_framework("SOC2", "v1")
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["frameworkName"] == "SOC2"

    def test_get_framework_not_found(self, framework_service):
        """Test getting a non-existent framework."""
        response = framework_service.get_framework("NOTFOUND", "v1")
        assert response["statusCode"] == 404

    def test_list_framework_versions(self, framework_service):
        """Test listing versions of a framework."""
        # Create multiple versions
        framework_service.create_or_update_framework(
            "SOC2", "v1", {"description": "Version 1"}
        )
        framework_service.create_or_update_framework(
            "SOC2", "v2", {"description": "Version 2"}
        )
        # List versions
        response = framework_service.list_framework_versions("SOC2")
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        assert body["frameworkName"] == "SOC2"

    def test_archive_framework(self, framework_service):
        """Test archiving a framework."""
        # Create
        framework_service.create_or_update_framework(
            "SOC2", "v1", {"description": "To Archive"}
        )
        # Archive
        response = framework_service.archive_framework("SOC2", "v1")
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ARCHIVED"

    def test_archive_framework_not_found(self, framework_service):
        """Test archiving a non-existent framework."""
        response = framework_service.archive_framework("NOTFOUND", "v1")
        assert response["statusCode"] == 404
