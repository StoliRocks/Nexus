"""Shared pytest fixtures for NexusAsyncAPIHandlerLambda tests."""

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
    os.environ["JOB_TABLE_NAME"] = "MappingJobs"
    os.environ["STATE_MACHINE_ARN"] = "arn:aws:states:us-east-1:123456789012:stateMachine:test"
    os.environ["FRAMEWORKS_TABLE_NAME"] = "Frameworks"
    os.environ["CONTROLS_TABLE_NAME"] = "FrameworkControls"
