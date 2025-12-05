"""Tests for SQS Trigger Lambda handler."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestLambdaHandler:
    """Tests for the lambda_handler function."""

    def test_handler_processes_valid_message(self, sample_sqs_event, state_machine_arn):
        """Test that handler processes a valid SQS message."""
        with patch(
            "nexus_sqs_trigger_lambda.handler.SqsTriggerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.start_workflow.return_value = (
                f"arn:aws:states:us-east-1:123456789012:execution:test-job-123"
            )

            from nexus_sqs_trigger_lambda.handler import lambda_handler

            result = lambda_handler(sample_sqs_event, None)

            assert result["batchItemFailures"] == []
            mock_service.start_workflow.assert_called_once_with(
                job_id="test-job-123",
                control_key="AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
                target_framework_key="NIST-SP-800-53#R5",
                target_control_ids=["AC-1", "AC-2"],
            )

    def test_handler_reports_failure_on_exception(self, sample_sqs_event):
        """Test that handler reports batch item failures on exception."""
        with patch(
            "nexus_sqs_trigger_lambda.handler.SqsTriggerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.start_workflow.side_effect = Exception("Step Functions error")

            from nexus_sqs_trigger_lambda.handler import lambda_handler

            result = lambda_handler(sample_sqs_event, None)

            assert len(result["batchItemFailures"]) == 1
            assert result["batchItemFailures"][0]["itemIdentifier"] == "msg-001"

    def test_handler_skips_invalid_json(self):
        """Test that handler skips messages with invalid JSON."""
        event = {
            "Records": [
                {
                    "messageId": "msg-001",
                    "body": "not valid json",
                    "receiptHandle": "receipt-001",
                }
            ]
        }

        with patch(
            "nexus_sqs_trigger_lambda.handler.SqsTriggerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            from nexus_sqs_trigger_lambda.handler import lambda_handler

            result = lambda_handler(event, None)

            # No failures reported - invalid JSON is dropped
            assert result["batchItemFailures"] == []
            mock_service.start_workflow.assert_not_called()

    def test_handler_skips_missing_required_fields(self):
        """Test that handler skips messages missing required fields."""
        event = {
            "Records": [
                {
                    "messageId": "msg-001",
                    "body": json.dumps({"job_id": "test-123"}),  # Missing other fields
                    "receiptHandle": "receipt-001",
                }
            ]
        }

        with patch(
            "nexus_sqs_trigger_lambda.handler.SqsTriggerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            from nexus_sqs_trigger_lambda.handler import lambda_handler

            result = lambda_handler(event, None)

            # No failures reported - incomplete messages are dropped
            assert result["batchItemFailures"] == []
            mock_service.start_workflow.assert_not_called()

    def test_handler_processes_multiple_messages(self):
        """Test that handler processes multiple messages in a batch."""
        event = {
            "Records": [
                {
                    "messageId": "msg-001",
                    "body": json.dumps(
                        {
                            "job_id": "job-1",
                            "control_key": "AWS#1.0#CTRL-1",
                            "target_framework_key": "NIST#R5",
                        }
                    ),
                },
                {
                    "messageId": "msg-002",
                    "body": json.dumps(
                        {
                            "job_id": "job-2",
                            "control_key": "AWS#1.0#CTRL-2",
                            "target_framework_key": "NIST#R5",
                        }
                    ),
                },
            ]
        }

        with patch(
            "nexus_sqs_trigger_lambda.handler.SqsTriggerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            from nexus_sqs_trigger_lambda.handler import lambda_handler

            result = lambda_handler(event, None)

            assert result["batchItemFailures"] == []
            assert mock_service.start_workflow.call_count == 2

    def test_handler_partial_batch_failure(self):
        """Test that handler reports partial batch failures correctly."""
        event = {
            "Records": [
                {
                    "messageId": "msg-001",
                    "body": json.dumps(
                        {
                            "job_id": "job-1",
                            "control_key": "AWS#1.0#CTRL-1",
                            "target_framework_key": "NIST#R5",
                        }
                    ),
                },
                {
                    "messageId": "msg-002",
                    "body": json.dumps(
                        {
                            "job_id": "job-2",
                            "control_key": "AWS#1.0#CTRL-2",
                            "target_framework_key": "NIST#R5",
                        }
                    ),
                },
            ]
        }

        with patch(
            "nexus_sqs_trigger_lambda.handler.SqsTriggerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            # First call succeeds, second fails
            mock_service.start_workflow.side_effect = [None, Exception("Error")]

            from nexus_sqs_trigger_lambda.handler import lambda_handler

            result = lambda_handler(event, None)

            # Only the second message should be in failures
            assert len(result["batchItemFailures"]) == 1
            assert result["batchItemFailures"][0]["itemIdentifier"] == "msg-002"
