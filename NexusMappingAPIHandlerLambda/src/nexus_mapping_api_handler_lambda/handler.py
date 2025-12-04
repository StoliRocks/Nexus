"""Mappings Handler Lambda - CRUD operations for control mappings endpoints."""

import json
from typing import Any

from pydantic import ValidationError

from nexus_mapping_api_handler_lambda.service import MappingService
from nexus_application_commons.dynamodb.response_builder import (
    error_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import BatchMappingsCreateRequest


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Handle mapping CRUD operations.

    Routes:
        GET  /mappings - List mappings with filters
        GET  /mappings/{mappingId} - Get specific mapping
        GET  /controls/{controlId}/mappings - Mappings for a control
        POST /batchMappings - Bulk create mappings
        PUT  /mappings/{mappingId}/archive - Archive mapping

    Args:
        event: API Gateway proxy event
        context: Lambda context (unused)

    Returns:
        API Gateway proxy response
    """
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    mapping_id = path_params.get("mappingId")
    control_id = path_params.get("controlId")

    service = MappingService()

    try:
        # Route based on method and path
        if http_method == "GET":
            if control_id:
                # GET /controls/{controlId}/mappings
                return service.get_mappings_for_control(control_id, query_params)
            elif mapping_id:
                # GET /mappings/{mappingId}
                return service.get_mapping(mapping_id)
            else:
                # GET /mappings
                return service.list_mappings(query_params)

        elif http_method == "POST":
            if path.endswith("/batchMappings"):
                # POST /batchMappings
                body = _parse_body(event)
                request = BatchMappingsCreateRequest.model_validate(body)
                return service.batch_create_mappings(request)
            return validation_error_response("Invalid POST endpoint")

        elif http_method == "PUT":
            if path.endswith("/archive") and mapping_id:
                # PUT /mappings/{mappingId}/archive
                return service.archive_mapping(mapping_id)
            return validation_error_response("Invalid PUT endpoint")

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
