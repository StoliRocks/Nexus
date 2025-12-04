"""Tests for NexusMappingFeedbackAPIHandlerLambda module."""

import json
import os
import pytest
import boto3
from moto import mock_aws
from pydantic import ValidationError

from nexus_mapping_feedback_api_handler_lambda.handler import lambda_handler
from nexus_mapping_feedback_api_handler_lambda.service import FeedbackService
from nexus_application_interface.api.v1 import FeedbackCreateRequest, FeedbackUpdateRequest


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
            TableName="MappingFeedbacks",
            KeySchema=[
                {"AttributeName": "mappingKey", "KeyType": "HASH"},
                {"AttributeName": "reviewerId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "mappingKey", "AttributeType": "S"},
                {"AttributeName": "reviewerId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb


@pytest.fixture
def feedback_service(dynamodb_table):
    """Create a FeedbackService with mocked DynamoDB."""
    return FeedbackService(dynamodb_resource=dynamodb_table, table_name="MappingFeedbacks")


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    @mock_aws
    def test_invalid_json_body(self, aws_credentials):
        """Test that invalid JSON body returns validation error."""
        # Create mock table for FeedbackService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingFeedbacks",
            KeySchema=[
                {"AttributeName": "mappingKey", "KeyType": "HASH"},
                {"AttributeName": "reviewerId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "mappingKey", "AttributeType": "S"},
                {"AttributeName": "reviewerId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "POST",
            "path": "/mappings/mapping123/feedbacks",
            "pathParameters": {"mappingId": "mapping123"},
            "body": "invalid json",
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    @mock_aws
    def test_method_not_allowed(self, aws_credentials):
        """Test that unsupported methods return 405."""
        # Create mock table for FeedbackService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="MappingFeedbacks",
            KeySchema=[
                {"AttributeName": "mappingKey", "KeyType": "HASH"},
                {"AttributeName": "reviewerId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "mappingKey", "AttributeType": "S"},
                {"AttributeName": "reviewerId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "DELETE",
            "path": "/mappings/mapping123/feedbacks",
            "pathParameters": {"mappingId": "mapping123"},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 405

    def test_missing_mapping_id(self):
        """Test that missing mappingId returns validation error."""
        event = {
            "httpMethod": "GET",
            "path": "/mappings//feedbacks",
            "pathParameters": {},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400


class TestFeedbackService:
    """Tests for FeedbackService class."""

    def test_list_feedbacks_empty(self, feedback_service):
        """Test listing feedbacks when none exist."""
        response = feedback_service.list_feedbacks("mapping123", {})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["feedbacks"] == []
        assert body["count"] == 0

    def test_create_feedback(self, feedback_service):
        """Test creating a new feedback."""
        request = FeedbackCreateRequest(
            feedbackProviderId="user@example.com",
            label="thumbs_up",
        )
        response = feedback_service.create_feedback("mapping123", request)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["mappingKey"] == "mapping123"
        assert body["label"] == "thumbs_up"

    def test_create_feedback_missing_provider(self, feedback_service):
        """Test creating feedback without feedbackProviderId raises validation error."""
        with pytest.raises(ValidationError):
            FeedbackCreateRequest(label="thumbs_up")

    def test_create_feedback_invalid_label(self, feedback_service):
        """Test creating feedback with invalid label raises validation error."""
        with pytest.raises(ValidationError):
            FeedbackCreateRequest(
                feedbackProviderId="user@example.com",
                label="invalid_label",
            )

    def test_create_duplicate_feedback(self, feedback_service):
        """Test creating duplicate feedback from same user."""
        request = FeedbackCreateRequest(
            feedbackProviderId="user@example.com",
            label="thumbs_up",
        )
        feedback_service.create_feedback("mapping123", request)
        # Try to create again
        request2 = FeedbackCreateRequest(
            feedbackProviderId="user@example.com",
            label="thumbs_down",
        )
        response = feedback_service.create_feedback("mapping123", request2)
        assert response["statusCode"] == 400

    def test_update_feedback(self, feedback_service):
        """Test updating an existing feedback."""
        # First create
        create_request = FeedbackCreateRequest(
            feedbackProviderId="user@example.com",
            label="thumbs_up",
        )
        feedback_service.create_feedback("mapping123", create_request)
        # Then update
        update_request = FeedbackUpdateRequest(label="thumbs_down")
        response = feedback_service.update_feedback(
            "mapping123",
            "user@example.com",
            update_request,
        )
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "Feedback updated successfully"

    def test_update_feedback_not_found(self, feedback_service):
        """Test updating a non-existent feedback."""
        update_request = FeedbackUpdateRequest(label="thumbs_down")
        response = feedback_service.update_feedback(
            "mapping123",
            "nonexistent@example.com",
            update_request,
        )
        assert response["statusCode"] == 404

    def test_list_feedbacks_after_create(self, feedback_service):
        """Test listing feedbacks after creating one."""
        request1 = FeedbackCreateRequest(
            feedbackProviderId="user1@example.com",
            label="thumbs_up",
        )
        feedback_service.create_feedback("mapping123", request1)
        request2 = FeedbackCreateRequest(
            feedbackProviderId="user2@example.com",
            label="thumbs_down",
        )
        feedback_service.create_feedback("mapping123", request2)
        response = feedback_service.list_feedbacks("mapping123", {})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
