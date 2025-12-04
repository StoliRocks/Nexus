"""Reviews Handler Lambda - CRUD operations for mapping reviews endpoints."""

import json
from typing import Any

from pydantic import ValidationError

from nexus_mapping_review_api_handler_lambda.service import ReviewService
from nexus_application_commons.dynamodb.response_builder import (
    error_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import ReviewCreateRequest, ReviewUpdateRequest


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Handle review CRUD operations.

    Routes:
        GET  /mappings/{mappingId}/reviews - List reviews for a mapping
        POST /mappings/{mappingId}/reviews - Submit a review
        PUT  /mappings/{mappingId}/reviews/{reviewId} - Update a review

    Args:
        event: API Gateway proxy event
        context: Lambda context (unused)

    Returns:
        API Gateway proxy response
    """
    http_method = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    mapping_id = path_params.get("mappingId")
    review_id = path_params.get("reviewId")

    if not mapping_id:
        return validation_error_response("mappingId is required")

    service = ReviewService()

    try:
        # Route based on method
        if http_method == "GET":
            # GET /mappings/{mappingId}/reviews
            return service.list_reviews(mapping_id, query_params)

        elif http_method == "POST":
            # POST /mappings/{mappingId}/reviews
            body = _parse_body(event)
            request = ReviewCreateRequest.model_validate(body)
            return service.create_review(mapping_id, request)

        elif http_method == "PUT":
            if not review_id:
                return validation_error_response("reviewId is required for PUT")
            # PUT /mappings/{mappingId}/reviews/{reviewId}
            body = _parse_body(event)
            update_request = ReviewUpdateRequest.model_validate(body)
            return service.update_review(mapping_id, review_id, update_request)

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
