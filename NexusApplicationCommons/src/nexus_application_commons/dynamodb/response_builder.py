"""API Gateway response builder utilities."""

import json
from typing import Any, Dict, Optional


def build_api_response(
    status_code: int,
    body: Any,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build an API Gateway proxy response.

    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)
        headers: Optional additional headers

    Returns:
        API Gateway proxy response dictionary
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    }

    if headers:
        default_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, default=str),
    }


def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Build a success response."""
    return build_api_response(status_code, data)


def created_response(data: Any) -> Dict[str, Any]:
    """Build a 201 Created response."""
    return build_api_response(201, data)


def accepted_response(data: Any) -> Dict[str, Any]:
    """Build a 202 Accepted response."""
    return build_api_response(202, data)


def error_response(
    message: str,
    status_code: int = 400,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build an error response.

    Args:
        message: Error message
        status_code: HTTP status code (default 400)
        error_code: Optional error code for programmatic handling
        details: Optional additional error details

    Returns:
        API Gateway proxy response dictionary
    """
    body: Dict[str, Any] = {"error": message}

    if error_code:
        body["errorCode"] = error_code
    if details:
        body["details"] = details

    return build_api_response(status_code, body)


def not_found_response(resource: str, identifier: str) -> Dict[str, Any]:
    """Build a 404 Not Found response."""
    return error_response(
        message=f"{resource} not found: {identifier}",
        status_code=404,
        error_code="NOT_FOUND",
    )


def validation_error_response(message: str, field: Optional[str] = None) -> Dict[str, Any]:
    """Build a 400 Validation Error response."""
    details = {"field": field} if field else None
    return error_response(
        message=message,
        status_code=400,
        error_code="VALIDATION_ERROR",
        details=details,
    )


def internal_error_response(message: str = "Internal server error") -> Dict[str, Any]:
    """Build a 500 Internal Server Error response."""
    return error_response(
        message=message,
        status_code=500,
        error_code="INTERNAL_ERROR",
    )
