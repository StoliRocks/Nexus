"""Job Updater Lambda - writes workflow results to job table."""

from typing import Any

from nexus_job_updater_lambda.service import JobUpdaterService


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Update job record with workflow results.

    Args:
        event: Dict with job_id, status (COMPLETED|FAILED), and results or error.
        context: Lambda context (unused).

    Returns:
        Dict with job_id, status, and count or error.

    Raises:
        ValueError: Unknown status specified.
    """
    service = JobUpdaterService()

    job_id = event.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")

    status = event.get("status")
    if not status:
        raise ValueError("status is required")

    if status == "COMPLETED":
        return service.update_job_completed(
            job_id=job_id,
            mappings=event.get("mappings", []),
            reasoning_results=event.get("reasoning", []),
        )
    elif status == "FAILED":
        return service.update_job_failed(
            job_id=job_id,
            error=event.get("error", {}),
        )
    else:
        raise ValueError(f"Unknown status: {status}")


# Alias for BATS Lambda configuration
api_endpoint_handler = lambda_handler
