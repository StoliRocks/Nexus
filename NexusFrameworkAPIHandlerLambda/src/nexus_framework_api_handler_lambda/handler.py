"""Frameworks Handler Lambda - CRUD operations for /api/v1/frameworks endpoints."""

import json
from typing import Any

from pydantic import ValidationError

from nexus_framework_api_handler_lambda.service import FrameworkService
from nexus_application_commons.dynamodb.response_builder import (
    error_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import FrameworkCreateRequest


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Handle framework CRUD operations.

    Routes:
        GET  /api/v1/frameworks - List all frameworks
        GET  /api/v1/frameworks/{frameworkName} - List versions of a framework
        GET  /api/v1/frameworks/{frameworkName}/{frameworkVersion} - Get specific framework
        PUT  /api/v1/frameworks/{frameworkName}/{frameworkVersion} - Create/update framework
        POST /api/v1/frameworks/{frameworkName}/{frameworkVersion}/archive - Archive framework

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

    service = FrameworkService()

    try:
        # Route based on method and path
        if http_method == "GET":
            if framework_name and framework_version:
                # GET /frameworks/{name}/{version}
                return service.get_framework(framework_name, framework_version)
            elif framework_name:
                # GET /frameworks/{name}
                return service.list_framework_versions(framework_name)
            else:
                # GET /frameworks
                query_params = event.get("queryStringParameters") or {}
                return service.list_frameworks(query_params)

        elif http_method == "PUT":
            if framework_name and framework_version:
                # PUT /frameworks/{name}/{version}
                body = _parse_body(event)
                request = FrameworkCreateRequest.model_validate(body)
                return service.create_or_update_framework(
                    framework_name, framework_version, request
                )
            return validation_error_response(
                "frameworkName and frameworkVersion required"
            )

        elif http_method == "POST":
            if path.endswith("/archive"):
                # POST /frameworks/{name}/{version}/archive
                if not framework_name or not framework_version:
                    return validation_error_response(
                        "frameworkName and frameworkVersion required for archive"
                    )
                return service.archive_framework(framework_name, framework_version)
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
