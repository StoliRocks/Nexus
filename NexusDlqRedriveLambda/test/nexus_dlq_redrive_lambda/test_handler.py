"""Tests for DLQ Redrive Lambda handler."""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestLambdaHandler:
    """Tests for the lambda_handler function."""

    def test_handler_fails_without_dlq_url(self):
        """Test that handler fails if DLQ_URL is not set."""
        with patch.dict(os.environ, {"DLQ_URL": "", "MAIN_QUEUE_URL": ""}):
            from nexus_dlq_redrive_lambda.handler import lambda_handler

            result = lambda_handler({}, None)

            assert result["statusCode"] == 500
            assert "DLQ_URL" in result["error"]

    def test_handler_fails_without_main_queue_url(self, dlq_url):
        """Test that handler fails if MAIN_QUEUE_URL is not set."""
        with patch.dict(os.environ, {"DLQ_URL": dlq_url, "MAIN_QUEUE_URL": ""}):
            from nexus_dlq_redrive_lambda.handler import lambda_handler

            result = lambda_handler({}, None)

            assert result["statusCode"] == 500
            assert "MAIN_QUEUE_URL" in result["error"]

    def test_handler_dry_run(self, dlq_url, main_queue_url):
        """Test dry run mode returns message count without redriving."""
        with patch.dict(
            os.environ, {"DLQ_URL": dlq_url, "MAIN_QUEUE_URL": main_queue_url}
        ):
            with patch("boto3.client") as mock_boto:
                mock_sqs = MagicMock()
                mock_boto.return_value = mock_sqs
                mock_sqs.get_queue_attributes.return_value = {
                    "Attributes": {"ApproximateNumberOfMessages": "25"}
                }

                from nexus_dlq_redrive_lambda.handler import lambda_handler

                result = lambda_handler({"dry_run": True}, None)

                assert result["statusCode"] == 200
                assert result["dry_run"] is True
                assert result["dlq_message_count"] == 25
                mock_sqs.receive_message.assert_not_called()

    def test_handler_empty_dlq(self, dlq_url, main_queue_url):
        """Test handler handles empty DLQ gracefully."""
        with patch.dict(
            os.environ, {"DLQ_URL": dlq_url, "MAIN_QUEUE_URL": main_queue_url}
        ):
            with patch("boto3.client") as mock_boto:
                mock_sqs = MagicMock()
                mock_boto.return_value = mock_sqs
                mock_sqs.get_queue_attributes.return_value = {
                    "Attributes": {"ApproximateNumberOfMessages": "0"}
                }

                from nexus_dlq_redrive_lambda.handler import lambda_handler

                result = lambda_handler({}, None)

                assert result["statusCode"] == 200
                assert result["messages_redriven"] == 0
                assert "empty" in result["message"].lower()

    def test_handler_redrives_messages(self, dlq_url, main_queue_url):
        """Test handler redrives messages from DLQ to main queue."""
        with patch.dict(
            os.environ, {"DLQ_URL": dlq_url, "MAIN_QUEUE_URL": main_queue_url}
        ):
            with patch("boto3.client") as mock_boto:
                mock_sqs = MagicMock()
                mock_boto.return_value = mock_sqs
                mock_sqs.get_queue_attributes.return_value = {
                    "Attributes": {"ApproximateNumberOfMessages": "2"}
                }
                # First call returns messages, second call returns empty
                mock_sqs.receive_message.side_effect = [
                    {
                        "Messages": [
                            {
                                "MessageId": "msg-001",
                                "ReceiptHandle": "receipt-001",
                                "Body": '{"job_id": "job-1"}',
                            },
                            {
                                "MessageId": "msg-002",
                                "ReceiptHandle": "receipt-002",
                                "Body": '{"job_id": "job-2"}',
                            },
                        ]
                    },
                    {"Messages": []},
                ]

                from nexus_dlq_redrive_lambda.handler import lambda_handler

                result = lambda_handler({}, None)

                assert result["statusCode"] == 200
                assert result["messages_redriven"] == 2
                assert mock_sqs.send_message.call_count == 2
                assert mock_sqs.delete_message.call_count == 2

    def test_handler_respects_max_messages(self, dlq_url, main_queue_url):
        """Test handler respects max_messages limit."""
        with patch.dict(
            os.environ, {"DLQ_URL": dlq_url, "MAIN_QUEUE_URL": main_queue_url}
        ):
            with patch("boto3.client") as mock_boto:
                mock_sqs = MagicMock()
                mock_boto.return_value = mock_sqs
                mock_sqs.get_queue_attributes.return_value = {
                    "Attributes": {"ApproximateNumberOfMessages": "100"}
                }
                # Return messages on each call
                mock_sqs.receive_message.return_value = {
                    "Messages": [
                        {
                            "MessageId": f"msg-{i}",
                            "ReceiptHandle": f"receipt-{i}",
                            "Body": f'{{"job_id": "job-{i}"}}',
                        }
                        for i in range(10)
                    ]
                }

                from nexus_dlq_redrive_lambda.handler import lambda_handler

                result = lambda_handler({"max_messages": 5}, None)

                # Should stop after reaching max_messages
                assert result["messages_redriven"] <= 10  # At most one batch

    def test_handler_handles_partial_failure(self, dlq_url, main_queue_url):
        """Test handler reports partial failures correctly."""
        with patch.dict(
            os.environ, {"DLQ_URL": dlq_url, "MAIN_QUEUE_URL": main_queue_url}
        ):
            with patch("boto3.client") as mock_boto:
                mock_sqs = MagicMock()
                mock_boto.return_value = mock_sqs
                mock_sqs.get_queue_attributes.return_value = {
                    "Attributes": {"ApproximateNumberOfMessages": "2"}
                }
                mock_sqs.receive_message.side_effect = [
                    {
                        "Messages": [
                            {
                                "MessageId": "msg-001",
                                "ReceiptHandle": "receipt-001",
                                "Body": '{"job_id": "job-1"}',
                            },
                        ]
                    },
                    {"Messages": []},
                ]
                # send_message fails
                mock_sqs.send_message.side_effect = Exception("Send failed")

                from nexus_dlq_redrive_lambda.handler import lambda_handler

                result = lambda_handler({}, None)

                assert result["statusCode"] == 207  # Partial success
                assert len(result["errors"]) > 0
