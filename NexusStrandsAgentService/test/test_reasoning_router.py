"""Tests for reasoning API router."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from nexus_strands_agent_service.app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_service():
    """Mock reasoning service."""
    with patch(
        "nexus_strands_agent_service.app.routers.reasoning.get_reasoning_service"
    ) as mock:
        service = MagicMock()
        service.generate_reasoning = AsyncMock(
            return_value="This AWS control maps to the NIST control because both address access control requirements."
        )
        service.generate_batch_reasoning = AsyncMock(
            return_value=[
                {
                    "control_id": "NIST-AC-1",
                    "reasoning": "Maps due to access control alignment",
                    "source_control_id": "AWS-IAM-001",
                    "status": "success",
                },
                {
                    "control_id": "NIST-AC-2",
                    "reasoning": "Maps due to account management",
                    "source_control_id": "AWS-IAM-001",
                    "status": "success",
                },
            ]
        )
        service.generate_consolidated_reasoning = AsyncMock(
            return_value="Consolidated analysis: The AWS IAM control maps to multiple NIST controls..."
        )
        mock.return_value = service
        yield service


class TestReasoningEndpoint:
    """Tests for POST /api/v1/reason."""

    def test_reason_success(self, client, mock_service):
        """Test successful reasoning generation."""
        response = client.post(
            "/api/v1/reason",
            json={
                "sourceControlId": "AWS-IAM-001",
                "sourceText": "Ensure IAM policies are attached only to groups or roles",
                "mapping": {
                    "targetControlId": "NIST-AC-1",
                    "targetFramework": "NIST-SP-800-53",
                    "text": "Access control policy and procedures",
                    "similarityScore": 0.85,
                    "rerankScore": 0.92,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sourceControlId"] == "AWS-IAM-001"
        assert data["targetControlId"] == "NIST-AC-1"
        assert data["status"] == "success"
        assert "reasoning" in data


class TestBatchReasoningEndpoint:
    """Tests for POST /api/v1/reason/batch."""

    def test_batch_reason_success(self, client, mock_service):
        """Test successful batch reasoning."""
        response = client.post(
            "/api/v1/reason/batch",
            json={
                "sourceControlId": "AWS-IAM-001",
                "sourceText": "Ensure IAM policies are attached only to groups or roles",
                "mappings": [
                    {
                        "targetControlId": "NIST-AC-1",
                        "targetFramework": "NIST-SP-800-53",
                        "text": "Access control policy",
                        "similarityScore": 0.85,
                        "rerankScore": 0.92,
                    },
                    {
                        "targetControlId": "NIST-AC-2",
                        "targetFramework": "NIST-SP-800-53",
                        "text": "Account management",
                        "similarityScore": 0.80,
                        "rerankScore": 0.88,
                    },
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["successful"] == 2
        assert len(data["results"]) == 2

    def test_batch_reason_too_many_mappings(self, client, mock_service):
        """Test batch reasoning rejects too many mappings."""
        mappings = [
            {
                "targetControlId": f"NIST-AC-{i}",
                "targetFramework": "NIST-SP-800-53",
                "text": f"Control {i}",
                "similarityScore": 0.8,
                "rerankScore": 0.85,
            }
            for i in range(25)
        ]

        response = client.post(
            "/api/v1/reason/batch",
            json={
                "sourceControlId": "AWS-IAM-001",
                "sourceText": "Test control",
                "mappings": mappings,
            },
        )

        assert response.status_code == 400
        assert "Maximum 20 mappings" in response.json()["detail"]


class TestConsolidatedReasoningEndpoint:
    """Tests for POST /api/v1/reason/consolidated."""

    def test_consolidated_reason_success(self, client, mock_service):
        """Test successful consolidated reasoning."""
        response = client.post(
            "/api/v1/reason/consolidated",
            json={
                "sourceControlId": "AWS-IAM-001",
                "sourceText": "Ensure IAM policies are attached only to groups or roles",
                "mappings": [
                    {
                        "targetControlId": "NIST-AC-1",
                        "targetFramework": "NIST-SP-800-53",
                        "text": "Access control policy",
                        "similarityScore": 0.85,
                        "rerankScore": 0.92,
                    },
                    {
                        "targetControlId": "NIST-AC-2",
                        "targetFramework": "NIST-SP-800-53",
                        "text": "Account management",
                        "similarityScore": 0.80,
                        "rerankScore": 0.88,
                    },
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sourceControlId"] == "AWS-IAM-001"
        assert data["mappingCount"] == 2
        assert data["status"] == "success"
        assert "consolidatedReasoning" in data

    def test_consolidated_reason_too_many_mappings(self, client, mock_service):
        """Test consolidated reasoning rejects too many mappings."""
        mappings = [
            {
                "targetControlId": f"NIST-AC-{i}",
                "targetFramework": "NIST-SP-800-53",
                "text": f"Control {i}",
                "similarityScore": 0.8,
                "rerankScore": 0.85,
            }
            for i in range(15)
        ]

        response = client.post(
            "/api/v1/reason/consolidated",
            json={
                "sourceControlId": "AWS-IAM-001",
                "sourceText": "Test control",
                "mappings": mappings,
            },
        )

        assert response.status_code == 400
        assert "Maximum 10 mappings" in response.json()["detail"]


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Nexus Strands Agent Service API"
        assert "endpoints" in data
