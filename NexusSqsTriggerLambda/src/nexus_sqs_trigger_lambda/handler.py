"""SQS Trigger Lambda Handler.

Consumes mapping requests from SQS queue and starts Step Functions workflow.
Provides durability for mapping requests - if Step Functions fails,
the message returns to SQS for retry or moves to DLQ after max retries.
"""

import json
import logging
from typing import Any, Dict, List

from nexus_sqs_trigger_lambda.service import SqsTriggerService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process SQS messages containing mapping requests and start Step Functions.

    Args:
        event: SQS event with Records array
        context: Lambda context

    Returns:
        Response with batchItemFailures for partial batch failure reporting
    """
    service = SqsTriggerService()
    batch_item_failures: List[Dict[str, str]] = []

    records = event.get("Records", [])
    logger.info(f"Processing {len(records)} SQS messages")

    for record in records:
        message_id = record.get("messageId", "unknown")
        try:
            # Parse the SQS message body
            body = json.loads(record.get("body", "{}"))

            job_id = body.get("job_id")
            control_key = body.get("control_key")
            target_framework_key = body.get("target_framework_key")
            target_control_ids = body.get("target_control_ids")

            if not all([job_id, control_key, target_framework_key]):
                logger.error(
                    f"Message {message_id} missing required fields: "
                    f"job_id={job_id}, control_key={control_key}, "
                    f"target_framework_key={target_framework_key}"
                )
                # Don't retry malformed messages - they will never succeed
                continue

            logger.info(
                f"Starting workflow for job_id={job_id}, "
                f"control_key={control_key}, target_framework_key={target_framework_key}"
            )

            # Start the Step Functions workflow
            service.start_workflow(
                job_id=job_id,
                control_key=control_key,
                target_framework_key=target_framework_key,
                target_control_ids=target_control_ids,
            )

            logger.info(f"Successfully started workflow for job_id={job_id}")

        except json.JSONDecodeError as e:
            logger.error(f"Message {message_id} has invalid JSON: {e}")
            # Don't retry malformed JSON - it will never succeed
            continue

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}", exc_info=True)
            # Add to failures for retry (or eventual DLQ)
            batch_item_failures.append({"itemIdentifier": message_id})

    response = {"batchItemFailures": batch_item_failures}

    if batch_item_failures:
        logger.warning(
            f"Batch completed with {len(batch_item_failures)} failures out of {len(records)}"
        )
    else:
        logger.info(f"Batch completed successfully: {len(records)} messages processed")

    return response


# Alias for BATS Lambda configuration
sqs_trigger_handler = lambda_handler
