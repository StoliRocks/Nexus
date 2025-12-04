"""Tests for NexusScienceOrchestratorLambda handler."""

import os
import pytest
import boto3
from decimal import Decimal
from moto import mock_aws
from unittest.mock import MagicMock

from nexus_science_orchestrator_lambda.handler import lambda_handler
from nexus_science_orchestrator_lambda.service import ScienceOrchestratorService
from nexus_science_orchestrator_lambda.science_client import ScienceClient


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Controls table with GSI
        dynamodb.create_table(
            TableName="Controls",
            KeySchema=[
                {"AttributeName": "frameworkKey", "KeyType": "HASH"},
                {"AttributeName": "controlKey", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "frameworkKey", "AttributeType": "S"},
                {"AttributeName": "controlKey", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "ControlKeyIndex",
                    "KeySchema": [{"AttributeName": "controlKey", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Frameworks table
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

        # Enrichment table
        dynamodb.create_table(
            TableName="Enrichment",
            KeySchema=[{"AttributeName": "control_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "control_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Embedding cache table
        dynamodb.create_table(
            TableName="EmbeddingCache",
            KeySchema=[
                {"AttributeName": "control_id", "KeyType": "HASH"},
                {"AttributeName": "model_version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "control_id", "AttributeType": "S"},
                {"AttributeName": "model_version", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield dynamodb


@pytest.fixture
def populated_tables(dynamodb_tables):
    """Populate tables with test data."""
    dynamodb = dynamodb_tables

    # Add controls
    controls_table = dynamodb.Table("Controls")
    controls_table.put_item(
        Item={
            "frameworkKey": "AWS.ControlCatalog#1.0",
            "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "controlId": "API_GW_CACHE_ENABLED",
            "title": "API Gateway Cache Enabled",
            "description": "Ensure API Gateway caching is enabled for improved performance.",
        }
    )

    # Add target framework controls
    for i in range(1, 4):
        controls_table.put_item(
            Item={
                "frameworkKey": "NIST-SP-800-53#R5",
                "controlKey": f"NIST-SP-800-53#R5#AC-{i}",
                "controlId": f"AC-{i}",
                "title": f"Access Control {i}",
                "description": f"Access control policy and procedures for AC-{i}.",
            }
        )

    # Add enrichment
    enrichment_table = dynamodb.Table("Enrichment")
    enrichment_table.put_item(
        Item={
            "control_id": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "enriched_text": "Enhanced: API Gateway caching improves response times and reduces backend load.",
        }
    )

    # Add framework
    frameworks_table = dynamodb.Table("Frameworks")
    frameworks_table.put_item(
        Item={
            "frameworkName": "NIST-SP-800-53",
            "version": "R5",
            "frameworkKey": "NIST-SP-800-53#R5",
            "displayName": "NIST SP 800-53 Revision 5",
        }
    )

    return dynamodb


@pytest.fixture
def mock_science_client():
    """Create a mock science client."""
    client = MagicMock(spec=ScienceClient)

    # Mock embedding
    client.call_embed.return_value = [0.1] * 4096

    # Mock retrieve
    client.call_retrieve.return_value = [
        {"control_id": "NIST-SP-800-53#R5#AC-1", "similarity_score": 0.92},
        {"control_id": "NIST-SP-800-53#R5#AC-2", "similarity_score": 0.85},
    ]

    # Mock rerank
    client.call_rerank.return_value = [
        {"control_id": "NIST-SP-800-53#R5#AC-1", "rerank_score": 0.95},
        {"control_id": "NIST-SP-800-53#R5#AC-2", "rerank_score": 0.88},
    ]

    return client


@pytest.fixture
def service(populated_tables, mock_science_client):
    """Create a ScienceOrchestratorService with mocked dependencies."""
    return ScienceOrchestratorService(
        dynamodb_resource=populated_tables,
        controls_table_name="Controls",
        frameworks_table_name="Frameworks",
        enrichment_table_name="Enrichment",
        embedding_cache_table_name="EmbeddingCache",
        science_client=mock_science_client,
    )


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    def test_unknown_action(self):
        """Test that unknown action raises ValueError."""
        event = {"action": "unknown_action"}
        with pytest.raises(ValueError, match="Unknown action"):
            lambda_handler(event, None)

    def test_missing_action(self):
        """Test that missing action raises ValueError."""
        event = {}
        with pytest.raises(ValueError, match="Unknown action"):
            lambda_handler(event, None)


class TestValidateControl:
    """Tests for validate_control action."""

    def test_validate_existing_control(self, service):
        """Test validating a control that exists."""
        event = {
            "action": "validate_control",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
        }
        result = service.validate_control(event)

        assert result["exists"] is True
        assert result["control"] is not None
        assert result["control_key"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"

    def test_validate_nonexistent_control(self, service):
        """Test validating a control that doesn't exist."""
        event = {
            "action": "validate_control",
            "control_key": "NONEXISTENT#1.0#CTRL-1",
        }
        result = service.validate_control(event)

        assert result["exists"] is False
        assert result["control"] is None

    def test_validate_control_from_components(self, service):
        """Test validating control using framework_key and control_id."""
        event = {
            "action": "validate_control",
            "framework_key": "AWS.ControlCatalog#1.0",
            "control_id": "API_GW_CACHE_ENABLED",
        }
        result = service.validate_control(event)

        assert result["exists"] is True
        assert result["control_key"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"

    def test_validate_control_missing_key(self, service):
        """Test validating without any control key."""
        event = {"action": "validate_control"}
        result = service.validate_control(event)

        assert result["exists"] is False
        assert "error" in result


class TestCheckEnrichment:
    """Tests for check_enrichment action."""

    def test_check_existing_enrichment(self, service):
        """Test checking enrichment that exists."""
        event = {
            "action": "check_enrichment",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
        }
        result = service.check_enrichment(event)

        assert result["exists"] is True
        assert result["enrichment"] is not None
        assert "enriched_text" in result["enrichment"]

    def test_check_nonexistent_enrichment(self, service):
        """Test checking enrichment that doesn't exist."""
        event = {
            "action": "check_enrichment",
            "control_key": "NONEXISTENT#1.0#CTRL-1",
        }
        result = service.check_enrichment(event)

        assert result["exists"] is False
        assert result["enrichment"] is None


class TestMapControl:
    """Tests for map_control action."""

    def test_map_control_success(self, service, mock_science_client):
        """Test successful control mapping."""
        event = {
            "action": "map_control",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework_key": "NIST-SP-800-53#R5",
        }
        result = service.map_control(event)

        assert "mappings" in result
        assert len(result["mappings"]) > 0
        assert result["source_control_key"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
        assert result["target_framework_key"] == "NIST-SP-800-53#R5"

        # Verify mapping structure
        mapping = result["mappings"][0]
        assert "target_control_key" in mapping
        assert "target_control_id" in mapping
        assert "similarity_score" in mapping
        assert "rerank_score" in mapping

    def test_map_control_with_target_ids(self, service, mock_science_client):
        """Test mapping with specific target control IDs."""
        event = {
            "action": "map_control",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework_key": "NIST-SP-800-53#R5",
            "target_control_ids": ["AC-1", "AC-2"],
        }
        result = service.map_control(event)

        assert "mappings" in result
        assert result["target_framework_key"] == "NIST-SP-800-53#R5"

    def test_map_control_missing_source(self, service):
        """Test mapping without source control."""
        event = {
            "action": "map_control",
            "target_framework_key": "NIST-SP-800-53#R5",
        }
        result = service.map_control(event)

        assert result["mappings"] == []
        assert "error" in result

    def test_map_control_missing_target(self, service):
        """Test mapping without target framework."""
        event = {
            "action": "map_control",
            "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
        }
        result = service.map_control(event)

        assert result["mappings"] == []
        assert "error" in result

    def test_map_control_with_legacy_params(self, service, mock_science_client):
        """Test mapping using legacy parameter names."""
        event = {
            "action": "map_control",
            "control_id": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            "target_framework": "NIST-SP-800-53",
            "target_version": "R5",
        }
        result = service.map_control(event)

        assert "mappings" in result
        assert result["target_framework_key"] == "NIST-SP-800-53#R5"


class TestScienceClient:
    """Tests for ScienceClient mock implementations."""

    def test_mock_embed(self):
        """Test mock embedding generation."""
        client = ScienceClient(use_mock=True)
        embedding = client.call_embed("test-id", "test text")

        assert len(embedding) == 4096
        # Check normalized (unit vector)
        norm = sum(x * x for x in embedding) ** 0.5
        assert abs(norm - 1.0) < 0.001

    def test_mock_retrieve(self):
        """Test mock retrieval."""
        client = ScienceClient(use_mock=True)
        candidates = client.call_retrieve(
            [0.1] * 4096,
            [[0.1] * 4096, [0.2] * 4096],
            ["CTRL-1", "CTRL-2"],
            top_k=2,
        )

        assert len(candidates) == 2
        assert all("control_id" in c for c in candidates)
        assert all("similarity_score" in c for c in candidates)
        # Check sorted by score descending
        assert candidates[0]["similarity_score"] >= candidates[1]["similarity_score"]

    def test_mock_rerank(self):
        """Test mock reranking."""
        client = ScienceClient(use_mock=True)
        rankings = client.call_rerank(
            "source text",
            [{"control_key": "CTRL-1", "text": "text 1"}],
            threshold=0.5,
        )

        assert isinstance(rankings, list)
        assert all("control_id" in r for r in rankings)
        assert all("rerank_score" in r for r in rankings)


class TestKeyBuilding:
    """Tests for key building utilities."""

    def test_parse_control_key(self, service):
        """Test parsing control key into components."""
        framework, version, control_id = service._parse_control_key(
            "NIST-SP-800-53#R5#AC-1"
        )
        assert framework == "NIST-SP-800-53"
        assert version == "R5"
        assert control_id == "AC-1"

    def test_parse_control_key_with_hash_in_id(self, service):
        """Test parsing control key with hash in control ID."""
        framework, version, control_id = service._parse_control_key(
            "Framework#1.0#CTRL#SUB"
        )
        assert framework == "Framework"
        assert version == "1.0"
        assert control_id == "CTRL#SUB"

    def test_build_framework_key(self, service):
        """Test building framework key."""
        key = service._build_framework_key("NIST-800-53", "R5")
        assert key == "NIST-800-53#R5"

    def test_build_framework_key_default_version(self, service):
        """Test building framework key with default version."""
        key = service._build_framework_key("NIST-800-53")
        assert key == "NIST-800-53#R5"  # Default from DEFAULT_FRAMEWORK_VERSIONS

    def test_build_control_key(self, service):
        """Test building control key."""
        key = service._build_control_key("NIST-800-53#R5", "AC-1")
        assert key == "NIST-800-53#R5#AC-1"
