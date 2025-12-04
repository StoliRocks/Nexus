"""Controls Handler Lambda - CRUD operations for framework controls endpoints."""

import json
from typing import Any

from pydantic import ValidationError

from nexus_control_api_handler_lambda.service import ControlService
from nexus_application_commons.dynamodb.response_builder import (
    error_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import (
    ControlCreateRequest,
    ControlUpdateRequest,
    BatchControlsCreateRequest,
    BatchArchiveRequest,
)


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Handle control CRUD operations.

    Routes:
        GET  /frameworks/{name}/{version}/controls - List controls
        GET  /frameworks/{name}/{version}/controls/{controlId} - Get control
        PUT  /frameworks/{name}/{version}/controls/{controlId} - Create/update control
        POST /frameworks/{name}/{version}/batchControls - Bulk create (up to 100)
        PUT  /frameworks/{name}/{version}/controls/{controlId}/archive - Archive control
        POST /frameworks/{name}/{version}/controls/batchArchive - Bulk archive

    Args:
        event: API Gateway proxy event
        context: Lambda context (unused)

    Returns:
        API Gateway proxy response
    """
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}

    framework_name = path_params.get("frameworkName")
    framework_version = path_params.get("frameworkVersion")
    control_id = path_params.get("controlId")

    if not framework_name or not framework_version:
        return validation_error_response(
            "frameworkName and frameworkVersion are required path parameters"
        )

    framework_key = f"{framework_name}#{framework_version}"
    service = ControlService()

    try:
        # Route based on method and path
        if http_method == "GET":
            if control_id:
                # GET /controls/{controlId}
                return service.get_control(framework_key, control_id)
            else:
                # GET /controls
                query_params = event.get("queryStringParameters") or {}
                return service.list_controls(framework_key, query_params)

        elif http_method == "PUT":
            if control_id:
                if path.endswith("/archive"):
                    # PUT /controls/{controlId}/archive
                    return service.archive_control(framework_key, control_id)
                else:
                    # PUT /controls/{controlId}
                    body = _parse_body(event)
                    # Use ControlCreateRequest for new, ControlUpdateRequest for existing
                    # The service will handle the distinction
                    request = ControlCreateRequest.model_validate(body)
                    return service.create_or_update_control(framework_key, control_id, request)
            return validation_error_response("controlId is required for PUT operations")

        elif http_method == "POST":
            if path.endswith("/batchControls"):
                # POST /batchControls
                body = _parse_body(event)
                batch_request = BatchControlsCreateRequest.model_validate(body)
                return service.batch_create_controls(framework_key, batch_request)
            elif path.endswith("/batchArchive"):
                # POST /controls/batchArchive
                body = _parse_body(event)
                archive_request = BatchArchiveRequest.model_validate(body)
                return service.batch_archive_controls(framework_key, archive_request)
            return validation_error_response("Invalid POST endpoint")

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
