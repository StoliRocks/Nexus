"""Tests for the embed router endpoint."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import numpy as np


class TestEmbedRouter:
    """Tests for POST /api/v1/embed endpoint."""

    @pytest.fixture
    def mock_models(self, mock_retriever):
        """Mock the MODELS dictionary."""
        return {"retriever": mock_retriever, "reranker": MagicMock()}

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

    @pytest.fixture
    def mock_cache_miss(self):
        """Mock cache service that always misses."""
        mock = MagicMock()
        mock.get_embedding = AsyncMock(return_value=None)
        mock.store_embedding = AsyncMock(return_value=None)
        return mock

    def test_embed_success_cache_miss(self, client, mock_cache_miss, mock_retriever):
        """Test successful embedding generation with cache miss."""
        with patch(
            "nexus_ecs_service.app.routers.embed.EmbeddingCacheService",
            return_value=mock_cache_miss
        ):
            with patch(
                "nexus_ecs_service.app.routers.embed.MODELS",
                {"retriever": mock_retriever}
            ):
                response = client.post(
                    "/api/v1/embed",
                    json={
                        "control_id": "IAM.21",
                        "text": "Ensure IAM users are managed through centralized identity provider"
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["control_id"] == "IAM.21"
        assert "embedding" in data
        assert len(data["embedding"]) == 4096
        assert data["cache_hit"] is False

    def test_embed_validation_error_missing_control_id(self, client):
        """Test validation error when control_id is missing."""
        response = client.post(
            "/api/v1/embed",
            json={
                "text": "Some control text"
            }
        )

        assert response.status_code == 422

    def test_embed_validation_error_missing_text(self, client):
        """Test validation error when text is missing."""
        response = client.post(
            "/api/v1/embed",
            json={
                "control_id": "IAM.21"
            }
        )

        assert response.status_code == 422
