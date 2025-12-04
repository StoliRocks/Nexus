"""Frameworks handler business logic."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union

import boto3
from boto3.dynamodb.conditions import Key

from nexus_application_commons.dynamodb.response_builder import (
    success_response,
    created_response,
    not_found_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import FrameworkCreateRequest

logger = logging.getLogger(__name__)

FRAMEWORKS_TABLE_NAME = os.environ.get("FRAMEWORKS_TABLE_NAME", "Frameworks")


class FrameworkService:
    """Service class for framework CRUD operations."""

    def __init__(self, dynamodb_resource: Optional[Any] = None, table_name: Optional[str] = None):
        """
        Initialize the framework service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            table_name: Optional table name override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or FRAMEWORKS_TABLE_NAME
        self.table = self.dynamodb.Table(self.table_name)

    def list_frameworks(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all frameworks with optional filtering.

        Args:
            query_params: Optional filters (status, nextToken, maxResults)

        Returns:
            API response with frameworks list
        """
        status_filter = query_params.get("status")
        max_results = min(int(query_params.get("maxResults", 100)), 100)

        scan_kwargs = {"Limit": max_results}

        if query_params.get("nextToken"):
            try:
                scan_kwargs["ExclusiveStartKey"] = json.loads(query_params["nextToken"])
            except json.JSONDecodeError:
                return validation_error_response("Invalid nextToken format")

        response = self.table.scan(**scan_kwargs)
        items = response.get("Items", [])

        # Filter by status if provided
        if status_filter:
            items = [i for i in items if i.get("status") == status_filter]

        result = {"frameworks": items, "count": len(items)}

        if response.get("LastEvaluatedKey"):
            result["nextToken"] = json.dumps(response["LastEvaluatedKey"])

        return success_response(result)

    def list_framework_versions(self, framework_name: str) -> Dict[str, Any]:
        """
        List all versions of a specific framework.

        Args:
            framework_name: Framework name to query

        Returns:
            API response with versions list
        """
        response = self.table.query(
            KeyConditionExpression=Key("frameworkName").eq(framework_name)
        )

        items = response.get("Items", [])
        if not items:
            return not_found_response("Framework", framework_name)

        return success_response({
            "frameworkName": framework_name,
            "versions": items,
            "count": len(items),
        })

    def get_framework(
        self, framework_name: str, framework_version: str
    ) -> Dict[str, Any]:
        """
        Get a specific framework by name and version.

        Args:
            framework_name: Framework name
            framework_version: Framework version

        Returns:
            API response with framework details
        """
        response = self.table.get_item(
            Key={"frameworkName": framework_name, "version": framework_version}
        )

        item = response.get("Item")
        if not item:
            return not_found_response(
                "Framework", f"{framework_name} version {framework_version}"
            )

        return success_response(item)

    def create_or_update_framework(
        self,
        framework_name: str,
        framework_version: str,
        request: Union[FrameworkCreateRequest, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create or update a framework.

        Args:
            framework_name: Framework name
            framework_version: Framework version
            request: FrameworkCreateRequest model or dict with framework details

        Returns:
            API response with created/updated framework
        """
        now = datetime.utcnow().isoformat()

        # Handle both DAO and dict for backward compatibility
        if isinstance(request, FrameworkCreateRequest):
            description = request.description or ""
            source = request.source or ""
            uri = request.uri or ""
            additional_info = request.additional_info or {}
        else:
            # Legacy dict support
            description = request.get("description", "")
            source = request.get("source", "")
            uri = request.get("uri", "")
            additional_info = request.get("additionalInfo", {})

        # Check if framework exists
        existing = self.table.get_item(
            Key={"frameworkName": framework_name, "version": framework_version}
        ).get("Item")

        framework_key = f"{framework_name}#{framework_version}"

        item = {
            "frameworkName": framework_name,
            "version": framework_version,
            "frameworkKey": framework_key,
            "status": "ACTIVE",
            "description": description,
            "source": source,
            "uri": uri,
            "additionalInfo": additional_info,
            "lastModifiedBy": {"system": "api"},
            "lastModifiedAt": now,
        }

        if existing:
            # Update - preserve createdBy and createdAt
            item["createdBy"] = existing.get("createdBy", {"system": "api"})
            item["createdAt"] = existing.get("createdAt", now)
            item["arn"] = existing.get(
                "arn", f"arn:aws:nexus:::framework/{framework_key}"
            )
        else:
            # Create new
            item["createdBy"] = {"system": "api"}
            item["createdAt"] = now
            item["arn"] = f"arn:aws:nexus:::framework/{framework_key}"

        self.table.put_item(Item=item)

        if existing:
            return success_response(item)
        else:
            return created_response(item)

    def archive_framework(
        self, framework_name: str, framework_version: str
    ) -> Dict[str, Any]:
        """
        Archive a framework (set status to ARCHIVED).

        Args:
            framework_name: Framework name
            framework_version: Framework version

        Returns:
            API response confirming archive
        """
        # Check if exists
        existing = self.table.get_item(
            Key={"frameworkName": framework_name, "version": framework_version}
        ).get("Item")

        if not existing:
            return not_found_response(
                "Framework", f"{framework_name} version {framework_version}"
            )

        if existing.get("status") == "ARCHIVED":
            return validation_error_response("Framework is already archived")

        # Update status
        self.table.update_item(
            Key={"frameworkName": framework_name, "version": framework_version},
            UpdateExpression="SET #status = :status, lastModifiedAt = :now",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "ARCHIVED",
                ":now": datetime.utcnow().isoformat(),
            },
        )

        framework_key = f"{framework_name}#{framework_version}"
        return success_response({
            "message": f"Framework '{framework_name}' version '{framework_version}' archived",
            "frameworkKey": framework_key,
            "status": "ARCHIVED",
        })
