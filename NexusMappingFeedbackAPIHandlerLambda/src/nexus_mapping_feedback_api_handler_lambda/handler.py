"""Feedback Handler Lambda - CRUD operations for /api/v1/mappings/{mappingId}/feedbacks endpoints."""

import json
from typing import Any

from pydantic import ValidationError

from nexus_mapping_feedback_api_handler_lambda.service import FeedbackService
from nexus_application_commons.dynamodb.response_builder import (
    error_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import FeedbackCreateRequest, FeedbackUpdateRequest


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Handle feedback CRUD operations.

    Routes:
        GET  /api/v1/mappings/{mappingId}/feedbacks - List feedbacks for a mapping
        POST /api/v1/mappings/{mappingId}/feedbacks - Create feedback
        PUT  /api/v1/mappings/{mappingId}/feedbacks/{feedbackId} - Update feedback

    Args:
        event: API Gateway proxy event
        context: Lambda context (unused)

    Returns:
        API Gateway proxy response
    """
    http_method = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}

    mapping_id = path_params.get("mappingId")
    feedback_id = path_params.get("feedbackId")

    if not mapping_id:
        return validation_error_response("mappingId is required")

    service = FeedbackService()

    try:
        # Route based on method
        if http_method == "GET":
            # GET /mappings/{mappingId}/feedbacks
            query_params = event.get("queryStringParameters") or {}
            return service.list_feedbacks(mapping_id, query_params)

        elif http_method == "POST":
            # POST /mappings/{mappingId}/feedbacks
            body = _parse_body(event)
            request = FeedbackCreateRequest.model_validate(body)
            return service.create_feedback(mapping_id, request)

        elif http_method == "PUT":
            # PUT /mappings/{mappingId}/feedbacks/{feedbackId}
            if not feedback_id:
                return validation_error_response("feedbackId is required for update")
            body = _parse_body(event)
            update_request = FeedbackUpdateRequest.model_validate(body)
            return service.update_feedback(mapping_id, feedback_id, update_request)

        return error_response(f"Method {http_method} not allowed", status_code=405)

    except json.JSONDecodeError:
        return validation_error_response("Invalid JSON body")
    except ValidationError as e:
        # Extract first error for user-friendly message
        errors = e.errors()
        if errors:
            field = ".".join(str(loc) for loc in errors[0].get("loc", []))
            msg = errors[0].get("msg", "Validation error")
            return validation_error_response(msg, field=field if field else None)
        return validation_error_response("Validation error")
    except Exception as e:
        return error_response(str(e), status_code=500)


def _parse_body(event: dict) -> dict:
    """Parse request body from event."""
    if event.get("body"):
        return json.loads(event["body"])
    return {}


# Alias for BATS Lambda configuration
api_endpoint_handler = lambda_handler
