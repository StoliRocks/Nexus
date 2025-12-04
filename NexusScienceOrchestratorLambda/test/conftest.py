"""Shared pytest fixtures for NexusScienceOrchestratorLambda tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def set_env_vars():
    """Set required environment variables for all tests."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["CONTROLS_TABLE_NAME"] = "Controls"
    os.environ["FRAMEWORKS_TABLE_NAME"] = "Frameworks"
    os.environ["ENRICHMENT_TABLE_NAME"] = "Enrichment"
    os.environ["EMBEDDING_CACHE_TABLE_NAME"] = "EmbeddingCache"
    os.environ["USE_MOCK_SCIENCE"] = "true"
