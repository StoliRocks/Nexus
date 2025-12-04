"""Tests for NexusMappingReviewAPIHandlerLambda module."""

import json
import os
import pytest
import boto3
from moto import mock_aws

from nexus_mapping_review_api_handler_lambda.handler import lambda_handler
from nexus_mapping_review_api_handler_lambda.service import ReviewService
from nexus_application_interface.api.v1 import ReviewCreateRequest


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
            TableName="MappingReviews",
            KeySchema=[
                {"AttributeName": "mappingKey", "KeyType": "HASH"},
                {"AttributeName": "reviewKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "mappingKey", "AttributeType": "S"},
                {"AttributeName": "reviewKey", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb


@pytest.fixture
def review_service(dynamodb_table):
    """Create a ReviewService with mocked DynamoDB."""
    return ReviewService(dynamodb_resource=dynamodb_table, table_name="MappingReviews")


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    def test_missing_mapping_id(self):
        """Test that missing mappingId returns validation error."""
        event = {
            "httpMethod": "GET",
            "path": "/mappings//reviews",
            "pathParameters": {},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400


class TestReviewService:
    """Tests for ReviewService class."""

    def test_list_reviews_empty(self, review_service):
        """Test listing reviews when none exist."""
        response = review_service.list_reviews("test-mapping", {})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["reviews"] == []
        assert body["count"] == 0

    def test_create_review(self, review_service):
        """Test creating a new review."""
        request = ReviewCreateRequest(reviewerId="user123", correct=True)
        response = review_service.create_review("test-mapping", request)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["mappingKey"] == "test-mapping"

    def test_create_review_missing_reviewer(self, review_service):
        """Test that creating review without reviewerId fails with validation error."""
        with pytest.raises(ValueError):
            ReviewCreateRequest(correct=True)  # Missing required reviewerId
