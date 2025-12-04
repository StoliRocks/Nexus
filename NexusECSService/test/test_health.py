"""Tests for health and readiness endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for /health and /ready endpoints."""

    @pytest.fixture
    def mock_models(self, mock_retriever, mock_reranker):
        """Mock the MODELS dictionary."""
        return {"retriever": mock_retriever, "reranker": mock_reranker}

    @pytest.fixture
    def client_models_loaded(self, mock_models):
        """Create test client with models loaded."""
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
    def client_models_loading(self):
        """Create test client with models still loading."""
        with patch("nexus_ecs_service.app.startup.MODELS", {}):
            with patch("nexus_ecs_service.app.main.MODELS", {}):
                with patch("nexus_ecs_service.app.main.MODEL_LOADING_STATE", {
                    "loading": True,
                    "loaded": False,
                    "error": None,
                    "started_at": 1000.0
                }):
                    from nexus_ecs_service.app.main import app
                    yield TestClient(app)

    @pytest.fixture
    def client_models_error(self):
        """Create test client with model loading error."""
        with patch("nexus_ecs_service.app.startup.MODELS", {}):
            with patch("nexus_ecs_service.app.main.MODELS", {}):
                with patch("nexus_ecs_service.app.main.MODEL_LOADING_STATE", {
                    "loading": False,
                    "loaded": False,
                    "error": "Failed to download model from S3",
                    "started_at": 1000.0
                }):
                    from nexus_ecs_service.app.main import app
                    yield TestClient(app)

    def test_health_models_loaded(self, client_models_loaded):
        """Test health check when models are loaded."""
        response = client_models_loaded.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["models_loaded"] is True
        assert "models" in data
        assert data["service"] == "nexus-ecs-service"

    def test_health_models_loading(self, client_models_loading):
        """Test health check when models are still loading."""
        response = client_models_loading.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "loading"
        assert data["models_loaded"] is False
        assert "loading_time_seconds" in data

    def test_health_models_error(self, client_models_error):
        """Test health check when model loading failed."""
        response = client_models_error.get("/health")

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert data["models_loaded"] is False
        assert "error" in data

    def test_ready_models_loaded(self, client_models_loaded):
        """Test readiness check when models are loaded."""
        response = client_models_loaded.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["models_loaded"] is True
        assert "models" in data

    def test_ready_models_loading(self, client_models_loading):
        """Test readiness check when models are still loading."""
        response = client_models_loading.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["models_loaded"] is False
        assert data["loading"] is True

    def test_root_endpoint(self, client_models_loaded):
        """Test root endpoint returns service info."""
        response = client_models_loaded.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Nexus ECS Service API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "health" in data
        assert "ready" in data
