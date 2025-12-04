"""Pytest configuration and fixtures for NexusECSService tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock
import numpy as np
import torch


@pytest.fixture
def mock_retriever():
    """Create a mock retriever model."""
    mock = MagicMock()

    def encode_side_effect(texts, batch_size=32, show_progress=False):
        # Return normalized embeddings of shape (len(texts), 4096)
        embeddings = np.random.randn(len(texts), 4096).astype(np.float32)
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        return torch.from_numpy(embeddings)

    mock.encode = MagicMock(side_effect=encode_side_effect)
    return mock


@pytest.fixture
def mock_reranker():
    """Create a mock reranker model."""
    mock = MagicMock()

    def predict_side_effect(pairs, batch_size=32, show_progress_bar=False):
        # Return scores between 0 and 1
        return np.random.rand(len(pairs)).astype(np.float32)

    mock.predict = MagicMock(side_effect=predict_side_effect)
    return mock


@pytest.fixture
def sample_embedding():
    """Create a sample normalized embedding."""
    embedding = np.random.randn(4096).astype(np.float32)
    embedding = embedding / np.linalg.norm(embedding)
    return embedding.tolist()


@pytest.fixture
def sample_embeddings():
    """Create sample normalized embeddings."""
    embeddings = np.random.randn(10, 4096).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    return embeddings.tolist()


@pytest.fixture
def sample_candidates():
    """Create sample candidate controls for reranking."""
    return [
        {"control_id": "CTRL-001", "text": "Ensure users are authenticated"},
        {"control_id": "CTRL-002", "text": "Enable MFA for all accounts"},
        {"control_id": "CTRL-003", "text": "Rotate access keys regularly"},
        {"control_id": "CTRL-004", "text": "Monitor login attempts"},
        {"control_id": "CTRL-005", "text": "Encrypt data at rest"},
    ]
