"""Shared pytest fixtures for NexusEnrichmentAgentLambda tests."""

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
    os.environ["ENRICHMENT_TABLE_NAME"] = "Enrichment"
    os.environ["STRANDS_SERVICE_ENDPOINT"] = ""  # Use mock by default
