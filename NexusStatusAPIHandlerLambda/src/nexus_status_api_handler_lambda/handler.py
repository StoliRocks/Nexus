"""Status Handler Lambda - returns mapping job status for GET /api/v1/mappings/{mappingId}."""

from typing import Any

from nexus_status_api_handler_lambda.service import StatusService
from nexus_application_commons.dynamodb.response_builder import (
    success_response,
    not_found_response,
    validation_error_response,
    error_response,
)


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Handle GET /api/v1/mappings/{mappingId} request.

    Args:
        event: API Gateway proxy event with pathParameters.mappingId.
        context: Lambda context (unused).

    Returns:
        API Gateway response with mapping job status and results (if completed).
    """
    service = StatusService()

    try:
        path_params = event.get("pathParameters", {}) or {}
        mapping_id = path_params.get("mappingId")

        if not mapping_id:
            return validation_error_response("mappingId is required", field="mappingId")

        return service.get_job_status(mapping_id)

    except Exception as e:
        return error_response(str(e), status_code=500)


# Alias for BATS Lambda configuration
api_endpoint_handler = lambda_handler
