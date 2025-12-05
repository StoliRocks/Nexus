"""DLQ Redrive Lambda Handler.

Redrives failed mapping requests from DLQ back to the main queue
after a bug fix has been deployed.

Can be invoked manually or on a schedule to retry failed requests.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DLQ_URL = os.environ.get("DLQ_URL", "")
MAIN_QUEUE_URL = os.environ.get("MAIN_QUEUE_URL", "")
MAX_MESSAGES_PER_INVOCATION = int(os.environ.get("MAX_MESSAGES_PER_INVOCATION", "100"))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Redrive messages from DLQ to main queue.

    Args:
        event: Optional event with configuration:
            - max_messages: Override MAX_MESSAGES_PER_INVOCATION
            - dry_run: If true, just count messages without redriving
        context: Lambda context

    Returns:
        Summary of redrive operation
    """
    sqs = boto3.client("sqs")

    # Validate configuration
    if not DLQ_URL:
        return {
            "statusCode": 500,
            "error": "DLQ_URL environment variable is not set",
        }

    if not MAIN_QUEUE_URL:
        return {
            "statusCode": 500,
            "error": "MAIN_QUEUE_URL environment variable is not set",
        }

    # Parse event parameters
    max_messages = event.get("max_messages", MAX_MESSAGES_PER_INVOCATION)
    dry_run = event.get("dry_run", False)

    logger.info(
        f"Starting DLQ redrive: max_messages={max_messages}, dry_run={dry_run}"
    )

    # Get DLQ message count first
    dlq_attributes = sqs.get_queue_attributes(
        QueueUrl=DLQ_URL,
        AttributeNames=["ApproximateNumberOfMessages"],
    )
    dlq_count = int(
        dlq_attributes.get("Attributes", {}).get("ApproximateNumberOfMessages", "0")
    )

    logger.info(f"DLQ contains approximately {dlq_count} messages")

    if dry_run:
        return {
            "statusCode": 200,
            "dry_run": True,
            "dlq_message_count": dlq_count,
            "message": f"Dry run complete. {dlq_count} messages in DLQ.",
        }

    if dlq_count == 0:
        return {
            "statusCode": 200,
            "messages_redriven": 0,
            "message": "DLQ is empty. Nothing to redrive.",
        }

    # Redrive messages
    messages_redriven = 0
    errors = []

    while messages_redriven < max_messages:
        # Receive messages from DLQ (max 10 at a time)
        batch_size = min(10, max_messages - messages_redriven)
        response = sqs.receive_message(
            QueueUrl=DLQ_URL,
            MaxNumberOfMessages=batch_size,
            WaitTimeSeconds=1,
            MessageAttributeNames=["All"],
        )

        messages = response.get("Messages", [])
        if not messages:
            logger.info("No more messages in DLQ")
            break

        for message in messages:
            message_id = message.get("MessageId", "unknown")
            receipt_handle = message.get("ReceiptHandle")
            body = message.get("Body", "{}")

            try:
                # Send to main queue
                sqs.send_message(
                    QueueUrl=MAIN_QUEUE_URL,
                    MessageBody=body,
                )

                # Delete from DLQ
                sqs.delete_message(
                    QueueUrl=DLQ_URL,
                    ReceiptHandle=receipt_handle,
                )

                messages_redriven += 1
                logger.info(f"Redriven message {message_id}")

            except Exception as e:
                error_msg = f"Failed to redrive message {message_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

    result = {
        "statusCode": 200,
        "messages_redriven": messages_redriven,
        "errors": errors if errors else None,
        "dlq_message_count_before": dlq_count,
    }

    if errors:
        result["statusCode"] = 207  # Partial success
        result["message"] = (
            f"Redriven {messages_redriven} messages with {len(errors)} errors"
        )
    else:
        result["message"] = f"Successfully redriven {messages_redriven} messages"

    logger.info(f"Redrive complete: {result['message']}")
    return result


def redrive_single_message(
    sqs_client: Any,
    dlq_url: str,
    main_queue_url: str,
    message_id: str,
) -> Dict[str, Any]:
    """
    Redrive a specific message by ID.

    This is useful for selective redriving during investigation.

    Args:
        sqs_client: Boto3 SQS client
        dlq_url: DLQ URL
        main_queue_url: Main queue URL
        message_id: Specific message ID to redrive

    Returns:
        Result of redrive operation
    """
    # This would require scanning DLQ messages to find by ID
    # For now, we just redrive all messages
    raise NotImplementedError(
        "Single message redrive not implemented. "
        "Use the main handler to redrive all messages."
    )


# Alias for BATS Lambda configuration
dlq_redrive_handler = lambda_handler
