"""Tests for enrichment API router."""

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
    """Mock enrichment service."""
    with patch(
        "nexus_strands_agent_service.app.routers.enrichment.get_enrichment_service"
    ) as mock:
        service = MagicMock()
        service.enrich_control = AsyncMock(
            return_value={
                "enriched_interpretation": {
                    "primary_objective": "Test objective",
                    "implementation_type": "Technical",
                },
                "agent_outputs": {"agent1": "output1"},
                "framework_profile_applied": None,
                "status": "success",
            }
        )
        service.generate_framework_profile = AsyncMock(
            return_value={
                "language_analysis": {"control_focus": {"primary_focus": "technical"}},
                "enrichment_guidance": {"enrichment_philosophy": "Focus on AWS services"},
            }
        )
        mock.return_value = service
        yield service


class TestEnrichmentEndpoint:
    """Tests for POST /api/v1/enrich."""

    def test_enrich_control_success(self, client, mock_service):
        """Test successful control enrichment."""
        response = client.post(
            "/api/v1/enrich",
            json={
                "metadata": {
                    "frameworkName": "NIST-SP-800-53",
                    "frameworkVersion": "R5",
                },
                "control": {
                    "shortId": "AC-1",
                    "title": "Access Control Policy",
                    "description": "Test description",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["controlId"] == "AC-1"
        assert data["status"] == "success"
        assert "enrichedInterpretation" in data

    def test_enrich_control_with_profile(self, client, mock_service):
        """Test enrichment with framework profile."""
        response = client.post(
            "/api/v1/enrich",
            json={
                "metadata": {
                    "frameworkName": "SOC-2",
                    "frameworkVersion": "2017",
                },
                "control": {
                    "shortId": "CC1.1",
                    "title": "Control Environment",
                    "description": "Test description",
                },
                "frameworkProfile": {
                    "language_analysis": {"control_focus": {"primary_focus": "governance"}},
                },
            },
        )

        assert response.status_code == 200
        mock_service.enrich_control.assert_called_once()


class TestBatchEnrichmentEndpoint:
    """Tests for POST /api/v1/enrich/batch."""

    def test_batch_enrich_success(self, client, mock_service):
        """Test successful batch enrichment."""
        response = client.post(
            "/api/v1/enrich/batch",
            json={
                "metadata": {
                    "frameworkName": "NIST-SP-800-53",
                    "frameworkVersion": "R5",
                },
                "controls": [
                    {"shortId": "AC-1", "title": "Test 1", "description": "Desc 1"},
                    {"shortId": "AC-2", "title": "Test 2", "description": "Desc 2"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2

    def test_batch_enrich_too_many_controls(self, client, mock_service):
        """Test batch enrichment rejects too many controls."""
        controls = [
            {"shortId": f"AC-{i}", "title": f"Test {i}", "description": f"Desc {i}"}
            for i in range(15)
        ]

        response = client.post(
            "/api/v1/enrich/batch",
            json={
                "metadata": {"frameworkName": "NIST", "frameworkVersion": "R5"},
                "controls": controls,
            },
        )

        assert response.status_code == 400
        assert "Maximum 10 controls" in response.json()["detail"]


class TestProfileGenerationEndpoint:
    """Tests for POST /api/v1/profile/generate."""

    def test_generate_profile_success(self, client, mock_service):
        """Test successful profile generation."""
        response = client.post(
            "/api/v1/profile/generate",
            json={
                "frameworkName": "SOC-2",
                "sampleControls": [
                    {"shortId": "CC1.1", "title": "Test 1", "description": "Desc 1"},
                    {"shortId": "CC1.2", "title": "Test 2", "description": "Desc 2"},
                    {"shortId": "CC1.3", "title": "Test 3", "description": "Desc 3"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["frameworkName"] == "SOC-2"
        assert data["status"] == "success"
        assert "profile" in data

    def test_generate_profile_too_few_samples(self, client, mock_service):
        """Test profile generation rejects too few samples."""
        response = client.post(
            "/api/v1/profile/generate",
            json={
                "frameworkName": "SOC-2",
                "sampleControls": [
                    {"shortId": "CC1.1", "title": "Test 1", "description": "Desc 1"},
                ],
            },
        )

        assert response.status_code == 400
        assert "At least 2 sample controls" in response.json()["detail"]
