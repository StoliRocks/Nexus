"""Tests for the retrieve router endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestRetrieveRouter:
    """Tests for POST /api/v1/retrieve endpoint."""

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

    def test_retrieve_success(self, client, sample_embedding, sample_embeddings):
        """Test successful similarity retrieval."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "source_embedding": sample_embedding,
                "target_embeddings": sample_embeddings,
                "top_k": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        assert len(data["candidates"]) == 5

        # Verify structure
        for candidate in data["candidates"]:
            assert "control_id" in candidate
            assert "similarity" in candidate
            assert isinstance(candidate["similarity"], float)

    def test_retrieve_top_k_larger_than_targets(self, client, sample_embedding, sample_embeddings):
        """Test when top_k exceeds number of targets."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "source_embedding": sample_embedding,
                "target_embeddings": sample_embeddings[:3],
                "top_k": 10
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 3  # Only 3 targets available

    def test_retrieve_single_target(self, client, sample_embedding, sample_embeddings):
        """Test retrieval with single target embedding."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "source_embedding": sample_embedding,
                "target_embeddings": [sample_embeddings[0]],
                "top_k": 1
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 1

    def test_retrieve_dimension_mismatch(self, client, sample_embedding, sample_embeddings):
        """Test error when embedding dimensions don't match."""
        # Create mismatched target
        mismatched_targets = [[0.1] * 100]  # Wrong dimension

        response = client.post(
            "/api/v1/retrieve",
            json={
                "source_embedding": sample_embedding,
                "target_embeddings": mismatched_targets,
                "top_k": 5
            }
        )

        assert response.status_code == 400
        assert "Dimension mismatch" in response.json()["detail"]

    def test_retrieve_validation_error_empty_targets(self, client, sample_embedding):
        """Test validation error when targets list is empty."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "source_embedding": sample_embedding,
                "target_embeddings": [],
                "top_k": 5
            }
        )

        assert response.status_code == 422

    def test_retrieve_sorted_by_similarity(self, client, sample_embedding, sample_embeddings):
        """Test that results are sorted by similarity descending."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "source_embedding": sample_embedding,
                "target_embeddings": sample_embeddings,
                "top_k": 10
            }
        )

        assert response.status_code == 200
        data = response.json()
        candidates = data["candidates"]

        # Verify descending order
        for i in range(len(candidates) - 1):
            assert candidates[i]["similarity"] >= candidates[i + 1]["similarity"]
