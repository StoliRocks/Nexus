"""Tests for the rerank router endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestRerankRouter:
    """Tests for POST /api/v1/rerank endpoint."""

    @pytest.fixture
    def mock_models(self, mock_retriever, mock_reranker):
        """Mock the MODELS dictionary."""
        return {"retriever": mock_retriever, "reranker": mock_reranker}

    @pytest.fixture
    def client(self, mock_models):
        """Create test client with mocked models."""
        with patch("nexus_ecs_service.app.startup.MODELS", mock_models):
            with patch("nexus_ecs_service.app.main.MODELS", mock_models):
                with patch("nexus_ecs_service.app.main.MODEL_LOADING_STATE", {
                    "loading": False,
                    "loaded": True,
                    "error": None,
                    "started_at": None
                }):
                    from nexus_ecs_service.app.main import app
                    yield TestClient(app)

    def test_rerank_success(self, client, mock_reranker, sample_candidates):
        """Test successful reranking."""
        with patch(
            "nexus_ecs_service.app.routers.rerank.MODELS",
            {"reranker": mock_reranker}
        ):
            response = client.post(
                "/api/v1/rerank",
                json={
                    "source_text": "Ensure users authenticate with MFA",
                    "candidates": [
                        {"control_id": c["control_id"], "text": c["text"]}
                        for c in sample_candidates
                    ]
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "rankings" in data
        assert len(data["rankings"]) == len(sample_candidates)

        # Verify structure
        for ranking in data["rankings"]:
            assert "control_id" in ranking
            assert "score" in ranking
            assert isinstance(ranking["score"], float)

    def test_rerank_sorted_by_score(self, client, mock_reranker, sample_candidates):
        """Test that results are sorted by score descending."""
        with patch(
            "nexus_ecs_service.app.routers.rerank.MODELS",
            {"reranker": mock_reranker}
        ):
            response = client.post(
                "/api/v1/rerank",
                json={
                    "source_text": "Ensure users authenticate with MFA",
                    "candidates": [
                        {"control_id": c["control_id"], "text": c["text"]}
                        for c in sample_candidates
                    ]
                }
            )

        assert response.status_code == 200
        data = response.json()
        rankings = data["rankings"]

        # Verify descending order
        for i in range(len(rankings) - 1):
            assert rankings[i]["score"] >= rankings[i + 1]["score"]

    def test_rerank_single_candidate(self, client, mock_reranker):
        """Test reranking with single candidate."""
        with patch(
            "nexus_ecs_service.app.routers.rerank.MODELS",
            {"reranker": mock_reranker}
        ):
            response = client.post(
                "/api/v1/rerank",
                json={
                    "source_text": "Ensure users authenticate with MFA",
                    "candidates": [
                        {"control_id": "CTRL-001", "text": "Enable MFA for accounts"}
                    ]
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["rankings"]) == 1

    def test_rerank_validation_error_empty_candidates(self, client):
        """Test validation error when candidates list is empty."""
        response = client.post(
            "/api/v1/rerank",
            json={
                "source_text": "Ensure users authenticate with MFA",
                "candidates": []
            }
        )

        assert response.status_code == 422

    def test_rerank_validation_error_missing_source_text(self, client, sample_candidates):
        """Test validation error when source_text is missing."""
        response = client.post(
            "/api/v1/rerank",
            json={
                "candidates": [
                    {"control_id": c["control_id"], "text": c["text"]}
                    for c in sample_candidates
                ]
            }
        )

        assert response.status_code == 422

    def test_rerank_validation_error_invalid_candidate_structure(self, client):
        """Test validation error when candidate is missing required fields."""
        response = client.post(
            "/api/v1/rerank",
            json={
                "source_text": "Ensure users authenticate with MFA",
                "candidates": [
                    {"control_id": "CTRL-001"}  # Missing 'text' field
                ]
            }
        )

        assert response.status_code == 422
