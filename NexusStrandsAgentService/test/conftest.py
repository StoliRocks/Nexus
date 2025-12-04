"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_enrichment_processor():
    """Mock ProfileDrivenMultiAgentProcessor."""
    processor = MagicMock()
    processor.interpret_control_intent.return_value = {
        "enriched_interpretation": {
            "primary_objective": "Test objective",
            "implementation_type": "Technical",
            "primary_services": [{"service": "AWS Config"}],
        },
        "agent_outputs": {
            "agent1_objective_classification": '{"primary_objective": "Test"}',
            "agent2_technical_filter": '{"implementation_type": "Technical"}',
        },
        "status": "success",
    }
    return processor


@pytest.fixture
def mock_reasoning_generator():
    """Mock ReasoningGenerator."""
    generator = MagicMock()
    generator.generate_reasoning.return_value = "This control maps because..."
    generator.generate_batch_reasoning.return_value = [
        {
            "control_id": "NIST-AC-1",
            "reasoning": "Maps due to access control alignment",
            "source_control_id": "AWS-IAM-001",
            "status": "success",
        }
    ]
    generator.generate_consolidated_reasoning.return_value = (
        "Consolidated reasoning for all mappings..."
    )
    return generator


@pytest.fixture
def sample_control():
    """Sample control for testing."""
    return {
        "shortId": "AC-1",
        "title": "Access Control Policy",
        "description": "The organization develops, documents, and disseminates access control policy.",
    }


@pytest.fixture
def sample_metadata():
    """Sample framework metadata for testing."""
    return {
        "frameworkName": "NIST-SP-800-53",
        "frameworkVersion": "R5",
    }


@pytest.fixture
def sample_mapping():
    """Sample mapping for testing."""
    return {
        "target_control_id": "NIST-AC-1",
        "target_framework": "NIST-SP-800-53",
        "text": "Access control policy and procedures",
        "similarity_score": 0.85,
        "rerank_score": 0.92,
    }
