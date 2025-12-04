"""Tests for NexusEnrichmentAgentLambda handler."""

import json
import os
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock

from nexus_enrichment_agent_lambda.handler import lambda_handler
from nexus_enrichment_agent_lambda.service import EnrichmentAgentService


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
            TableName="Enrichment",
            KeySchema=[{"AttributeName": "control_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "control_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb


@pytest.fixture
def service(dynamodb_table):
    """Create an EnrichmentAgentService with mocked DynamoDB."""
    return EnrichmentAgentService(
        dynamodb_resource=dynamodb_table,
        enrichment_table_name="Enrichment",
        strands_endpoint="",  # Use mock
    )


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    def test_missing_control_key(self):
        """Test that missing control_key returns error."""
        event = {"control": {"title": "Test Control"}}
        response = lambda_handler(event, None)

        assert response["status"] == "error"
        assert "control_key is required" in response["error"]

    def test_successful_enrichment(self, dynamodb_table):
        """Test successful control enrichment."""
        with patch(
            "nexus_enrichment_agent_lambda.handler.EnrichmentAgentService"
        ) as MockService:
            mock_service = MagicMock()
            mock_service.enrich_control.return_value = {
                "enriched_text": "Enriched control text with semantic richness.",
                "enrichment_data": {"securityObjective": "Test objective"},
            }
            MockService.return_value = mock_service

            event = {
                "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
                "control": {
                    "title": "API Gateway Cache Enabled",
                    "description": "Ensure API Gateway caching is enabled.",
                },
            }

            response = lambda_handler(event, None)

            assert response["status"] == "success"
            assert response["control_key"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
            assert "enriched_text" in response

    def test_enrichment_error(self, dynamodb_table):
        """Test handling of enrichment errors."""
        with patch(
            "nexus_enrichment_agent_lambda.handler.EnrichmentAgentService"
        ) as MockService:
            mock_service = MagicMock()
            mock_service.enrich_control.side_effect = RuntimeError("Service unavailable")
            MockService.return_value = mock_service

            event = {
                "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
                "control": {"title": "Test Control"},
            }

            response = lambda_handler(event, None)

            assert response["status"] == "error"
            assert "Service unavailable" in response["error"]


class TestEnrichmentAgentService:
    """Tests for EnrichmentAgentService class."""

    def test_enrich_control_with_mock(self, service):
        """Test enrichment using mock strands service."""
        control_key = "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
        control = {
            "title": "API Gateway Cache Enabled",
            "description": "Ensure API Gateway caching is enabled for improved performance.",
        }

        result = service.enrich_control(control_key, control)

        assert "enriched_text" in result
        assert len(result["enriched_text"]) > 0
        assert "enrichment_data" in result

    def test_enrich_control_stores_in_dynamodb(self, service, dynamodb_table):
        """Test that enrichment is stored in DynamoDB."""
        control_key = "NIST-SP-800-53#R5#AC-1"
        control = {
            "title": "Access Control Policy",
            "description": "The organization develops access control policies.",
        }

        service.enrich_control(control_key, control)

        # Verify stored in DynamoDB
        table = dynamodb_table.Table("Enrichment")
        response = table.get_item(Key={"control_id": control_key})

        assert "Item" in response
        assert response["Item"]["control_id"] == control_key
        assert "enriched_text" in response["Item"]
        assert "original_text" in response["Item"]
        assert "created_at" in response["Item"]

    def test_enrich_control_with_metadata(self, service):
        """Test enrichment with framework metadata."""
        control_key = "SOC2#2017#CC1.1"
        control = {
            "title": "Control Environment",
            "description": "The organization demonstrates commitment to integrity.",
            "metadata": {
                "frameworkName": "SOC2",
                "frameworkVersion": "2017",
            },
        }

        result = service.enrich_control(control_key, control)

        assert "enriched_text" in result

    def test_enrich_control_text_fallback(self, service):
        """Test fallback to different text fields."""
        control_key = "TEST#1.0#CTRL-1"

        # Test with 'text' field
        control = {"text": "Control text content"}
        result = service.enrich_control(control_key, control)
        assert "enriched_text" in result

        # Test with 'title' only
        control = {"title": "Control Title Only"}
        result = service.enrich_control(control_key, control)
        assert "enriched_text" in result


class TestParseControlKey:
    """Tests for control key parsing."""

    def test_parse_full_control_key(self, service):
        """Test parsing full control key."""
        framework, version, control_id = service._parse_control_key(
            "NIST-SP-800-53#R5#AC-1"
        )
        assert framework == "NIST-SP-800-53"
        assert version == "R5"
        assert control_id == "AC-1"

    def test_parse_control_key_with_hash_in_id(self, service):
        """Test parsing control key with hash in control ID."""
        framework, version, control_id = service._parse_control_key(
            "AWS.Config#1.0#S3#BUCKET#VERSIONING"
        )
        assert framework == "AWS.Config"
        assert version == "1.0"
        assert control_id == "S3#BUCKET#VERSIONING"

    def test_parse_two_part_key(self, service):
        """Test parsing two-part key (no version)."""
        framework, version, control_id = service._parse_control_key("Framework#CTRL-1")
        assert framework == "Framework"
        assert version == "1.0"  # Default version
        assert control_id == "CTRL-1"

    def test_parse_single_part_key(self, service):
        """Test parsing single-part key (legacy)."""
        framework, version, control_id = service._parse_control_key("CTRL-123")
        assert framework == "Unknown"
        assert version == "1.0"
        assert control_id == "CTRL-123"


class TestMockEnrichment:
    """Tests for mock enrichment functionality."""

    def test_mock_enrich_response_structure(self, service):
        """Test mock enrichment returns proper structure."""
        result = service._mock_enrich(
            control_id="AC-1",
            title="Access Control",
            description="Original description text.",
        )

        assert "controlId" in result
        assert result["controlId"] == "AC-1"
        assert "enrichedInterpretation" in result
        assert "enrichedText" in result["enrichedInterpretation"]
        assert "securityObjective" in result["enrichedInterpretation"]
        assert "status" in result
        assert result["status"] == "success"

    def test_mock_enrich_includes_original_text(self, service):
        """Test mock enrichment includes original text."""
        original = "This is the original control description."
        result = service._mock_enrich(
            control_id="TEST-1",
            title="Test Control",
            description=original,
        )

        enriched = result["enrichedInterpretation"]["enrichedText"]
        assert original in enriched


class TestStrandsServiceIntegration:
    """Tests for strands service integration."""

    def test_call_strands_with_endpoint(self, dynamodb_table):
        """Test calling strands service when endpoint is configured."""
        service = EnrichmentAgentService(
            dynamodb_resource=dynamodb_table,
            enrichment_table_name="Enrichment",
            strands_endpoint="http://localhost:8000",
        )

        # Mock the HTTP request
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "controlId": "AC-1",
            "enrichedInterpretation": {
                "enrichedText": "Enriched from strands service",
                "securityObjective": "Test objective",
            },
            "status": "success",
        }).encode("utf-8")

        with patch.object(service.http, "request", return_value=mock_response):
            result = service._call_strands_enrich(
                control_id="AC-1",
                title="Access Control",
                description="Test description",
                metadata={"frameworkName": "NIST", "frameworkVersion": "R5"},
            )

            assert result["controlId"] == "AC-1"
            assert "enrichedInterpretation" in result

    def test_call_strands_error_handling(self, dynamodb_table):
        """Test error handling for strands service failures."""
        service = EnrichmentAgentService(
            dynamodb_resource=dynamodb_table,
            enrichment_table_name="Enrichment",
            strands_endpoint="http://localhost:8000",
        )

        # Mock failed HTTP request
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.data = b"Internal Server Error"

        with patch.object(service.http, "request", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Strands service error"):
                service._call_strands_enrich(
                    control_id="AC-1",
                    title="Test",
                    description="Test",
                    metadata={},
                )
