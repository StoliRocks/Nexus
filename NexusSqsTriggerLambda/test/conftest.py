"""Pytest configuration and fixtures for NexusSqsTriggerLambda tests."""

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
def state_machine_arn():
    """Sample Step Functions state machine ARN."""
    return "arn:aws:states:us-east-1:123456789012:stateMachine:MappingWorkflow"


@pytest.fixture
def sample_sqs_message():
    """Sample SQS message for testing."""
    return {
        "job_id": "test-job-123",
        "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
        "target_framework_key": "NIST-SP-800-53#R5",
        "target_control_ids": ["AC-1", "AC-2"],
    }


@pytest.fixture
def sample_sqs_event(sample_sqs_message):
    """Sample SQS event for Lambda handler testing."""
    import json

    return {
        "Records": [
            {
                "messageId": "msg-001",
                "body": json.dumps(sample_sqs_message),
                "receiptHandle": "receipt-001",
                "attributes": {
                    "ApproximateReceiveCount": "1",
                },
            }
        ]
    }
