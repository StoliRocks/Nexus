"""Tests for NexusMappingAPIHandlerLambda module."""

import json
import os
import pytest
import boto3
from moto import mock_aws

from nexus_mapping_api_handler_lambda.handler import lambda_handler
from nexus_mapping_api_handler_lambda.service import MappingService
from nexus_application_interface.api.v1 import BatchMappingsCreateRequest


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
            TableName="ControlMappings",
            KeySchema=[
                {"AttributeName": "controlKey", "KeyType": "HASH"},
                {"AttributeName": "mappedControlKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "controlKey", "AttributeType": "S"},
                {"AttributeName": "mappedControlKey", "AttributeType": "S"},
                {"AttributeName": "mappingKey", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "MappingKeyIndex",
                    "KeySchema": [{"AttributeName": "mappingKey", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "StatusIndex",
                    "KeySchema": [
                        {"AttributeName": "status", "KeyType": "HASH"},
                        {"AttributeName": "mappingKey", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb


@pytest.fixture
def mapping_service(dynamodb_table):
    """Create a MappingService with mocked DynamoDB."""
    return MappingService(dynamodb_resource=dynamodb_table, table_name="ControlMappings")


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    @mock_aws
    def test_invalid_json_body(self, aws_credentials):
        """Test that invalid JSON body returns validation error."""
        # Create mock table for MappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="ControlMappings",
            KeySchema=[
                {"AttributeName": "controlKey", "KeyType": "HASH"},
                {"AttributeName": "mappedControlKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "controlKey", "AttributeType": "S"},
                {"AttributeName": "mappedControlKey", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "POST",
            "path": "/batchMappings",
            "pathParameters": {},
            "body": "invalid json",
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    @mock_aws
    def test_method_not_allowed(self, aws_credentials):
        """Test that unsupported methods return 405."""
        # Create mock table for MappingService
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="ControlMappings",
            KeySchema=[
                {"AttributeName": "controlKey", "KeyType": "HASH"},
                {"AttributeName": "mappedControlKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "controlKey", "AttributeType": "S"},
                {"AttributeName": "mappedControlKey", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        event = {
            "httpMethod": "DELETE",
            "path": "/mappings",
            "pathParameters": {},
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 405


class TestMappingService:
    """Tests for MappingService class."""

    def test_list_mappings_empty(self, mapping_service):
        """Test listing mappings when none exist."""
        response = mapping_service.list_mappings({})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["mappings"] == []
        assert body["count"] == 0

    def test_batch_create_mappings(self, mapping_service):
        """Test batch creating mappings."""
        request = BatchMappingsCreateRequest(
            mappings=[
                {"sourceControlKey": "SOC2#v1#CC1.1", "targetControlKey": "NIST#v1#AC-1"},
                {"sourceControlKey": "SOC2#v1#CC1.2", "targetControlKey": "NIST#v1#AC-2"},
            ]
        )
        response = mapping_service.batch_create_mappings(request)
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["createdCount"] == 2

    def test_batch_create_empty(self, mapping_service):
        """Test batch create with empty list raises validation error."""
        with pytest.raises(Exception):
            BatchMappingsCreateRequest(mappings=[])

    def test_batch_create_missing_fields(self, mapping_service):
        """Test batch create with missing required fields raises validation error."""
        with pytest.raises(Exception):
            BatchMappingsCreateRequest(mappings=[{"sourceControlKey": "SOC2#v1#CC1.1"}])

    def test_get_mapping(self, mapping_service):
        """Test getting a mapping."""
        # First create
        request = BatchMappingsCreateRequest(
            mappings=[{"sourceControlKey": "SOC2#v1#CC1.1", "targetControlKey": "NIST#v1#AC-1"}]
        )
        mapping_service.batch_create_mappings(request)
        # Generate expected mapping key (sorted alphabetically, # separator)
        mapping_key = "NIST#v1#AC-1#SOC2#v1#CC1.1"
        # Then get
        response = mapping_service.get_mapping(mapping_key)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["mappingKey"] == mapping_key

    def test_get_mapping_not_found(self, mapping_service):
        """Test getting a non-existent mapping."""
        response = mapping_service.get_mapping("NOTFOUND")
        assert response["statusCode"] == 404

    def test_get_mappings_for_control(self, mapping_service):
        """Test getting mappings for a control."""
        # Create mappings
        request = BatchMappingsCreateRequest(
            mappings=[
                {"sourceControlKey": "SOC2#v1#CC1.1", "targetControlKey": "NIST#v1#AC-1"},
                {"sourceControlKey": "SOC2#v1#CC1.1", "targetControlKey": "NIST#v1#AC-2"},
            ]
        )
        mapping_service.batch_create_mappings(request)
        # Get mappings for control
        response = mapping_service.get_mappings_for_control("SOC2#v1#CC1.1", {})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2

    def test_archive_mapping(self, mapping_service):
        """Test archiving a mapping."""
        # Create
        request = BatchMappingsCreateRequest(
            mappings=[{"sourceControlKey": "SOC2#v1#CC1.1", "targetControlKey": "NIST#v1#AC-1"}]
        )
        mapping_service.batch_create_mappings(request)
        # Mapping key uses # separator (sorted alphabetically)
        mapping_key = "NIST#v1#AC-1#SOC2#v1#CC1.1"
        # Archive
        response = mapping_service.archive_mapping(mapping_key)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ARCHIVED"

    def test_archive_mapping_not_found(self, mapping_service):
        """Test archiving a non-existent mapping."""
        response = mapping_service.archive_mapping("NOTFOUND")
        assert response["statusCode"] == 404

    def test_archive_already_archived(self, mapping_service):
        """Test archiving an already archived mapping."""
        # Create and archive
        request = BatchMappingsCreateRequest(
            mappings=[{"sourceControlKey": "SOC2#v1#CC1.1", "targetControlKey": "NIST#v1#AC-1"}]
        )
        mapping_service.batch_create_mappings(request)
        # Mapping key uses # separator (sorted alphabetically)
        mapping_key = "NIST#v1#AC-1#SOC2#v1#CC1.1"
        mapping_service.archive_mapping(mapping_key)
        # Try to archive again
        response = mapping_service.archive_mapping(mapping_key)
        assert response["statusCode"] == 400
