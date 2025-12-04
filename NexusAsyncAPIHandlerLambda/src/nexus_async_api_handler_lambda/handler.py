"""Async Handler Lambda - receives POST /api/v1/mappings and starts Step Functions.

Supports Nexus Database Schema:
- control_key: Full control key (frameworkKey#controlId), e.g., "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
- target_framework_key: Framework key, e.g., "NIST-SP-800-53#R5"
"""

import json
from typing import Any

from pydantic import ValidationError

from nexus_async_api_handler_lambda.service import AsyncMappingService
from nexus_application_commons.dynamodb.response_builder import (
    accepted_response,
    validation_error_response,
    error_response,
)


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Handle POST /api/v1/mappings request.

    Args:
        event: API Gateway proxy event with body containing:
            - control_key: Full control key (required), format: frameworkName#version#controlId
            - target_framework_key: Target framework key (required), format: frameworkName#version
            - target_control_ids: Optional list of specific control IDs to map to
        context: Lambda context (unused).

    Returns:
        API Gateway response with 202 and mappingId on success, 400 on validation error.
    """
    service = AsyncMappingService()

    try:
        # Parse JSON body
        body = _parse_body(event)

        # Extract fields (support legacy field name)
        control_key = body.get("control_key") or body.get("controlKey") or body.get("control_id")
        target_framework_key = body.get("target_framework_key") or body.get("targetFrameworkKey")
        target_control_ids = body.get("target_control_ids") or body.get("targetControlIds")

        # ==========================================================================
        # Format Validation
        # ==========================================================================

        error = service.validate_control_key_format(control_key)
        if error:
            return validation_error_response(error, field="control_key")

        error = service.validate_framework_key_format(target_framework_key)
        if error:
            return validation_error_response(error, field="target_framework_key")

        if target_control_ids is not None:
            error = service.validate_target_control_ids(target_control_ids)
            if error:
                return validation_error_response(error, field="target_control_ids")

        # ==========================================================================
        # Database Validation
        # ==========================================================================

        exists, suggestion = service.control_exists(control_key)
        if not exists:
            msg = f"Control '{control_key}' not found in database"
            if suggestion:
                msg += f". {suggestion}"
            return validation_error_response(msg, field="control_key")

        exists, available = service.framework_exists(target_framework_key)
        if not exists:
            msg = f"Framework '{target_framework_key}' not found in database"
            if available:
                msg += f". Available: {available[:5]}"
            return validation_error_response(msg, field="target_framework_key")

        # ==========================================================================
        # Create Job and Start Workflow
        # ==========================================================================

        job_id = service.create_job(control_key, target_framework_key, target_control_ids)
        service.start_workflow(job_id, control_key, target_framework_key, target_control_ids)

        # Build status URL per HLD: /api/v1/mappings/{mappingId}
        request_context = event.get("requestContext", {})
        domain = request_context.get("domainName", "")
        stage = request_context.get("stage", "api")
        status_url = (
            f"https://{domain}/{stage}/v1/mappings/{job_id}"
            if domain
            else f"/api/v1/mappings/{job_id}"
        )

        return accepted_response({
            "mappingId": job_id,
            "status": "ACCEPTED",
            "statusUrl": status_url,
            "controlKey": control_key,
            "targetFrameworkKey": target_framework_key,
        })

    except json.JSONDecodeError:
        return validation_error_response("Invalid JSON body")
    except ValidationError as e:
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
