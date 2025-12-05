"""Pytest configuration and fixtures for NexusDlqRedriveLambda tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dlq_url():
    """Sample DLQ URL."""
    return "https://sqs.us-east-1.amazonaws.com/123456789012/MappingRequestDLQ"


@pytest.fixture
def main_queue_url():
    """Sample main queue URL."""
    return "https://sqs.us-east-1.amazonaws.com/123456789012/MappingRequestQueue"
