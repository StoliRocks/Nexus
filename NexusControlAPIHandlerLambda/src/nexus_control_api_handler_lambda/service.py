"""Controls handler business logic."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

from nexus_application_commons.dynamodb.response_builder import (
    success_response,
    created_response,
    accepted_response,
    not_found_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import (
    ControlCreateRequest,
    BatchControlsCreateRequest,
    BatchArchiveRequest,
)

logger = logging.getLogger(__name__)

CONTROLS_TABLE_NAME = os.environ.get("CONTROLS_TABLE_NAME", "FrameworkControls")
MAX_BATCH_SIZE = 100


class ControlService:
    """Service class for control CRUD operations."""

    def __init__(
        self, dynamodb_resource: Optional[Any] = None, table_name: Optional[str] = None
    ):
        """
        Initialize the control service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            table_name: Optional table name override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or CONTROLS_TABLE_NAME
        self.table = self.dynamodb.Table(self.table_name)

    def list_controls(
        self, framework_key: str, query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        List all controls for a framework with pagination.

        Args:
            framework_key: Framework key (frameworkName#version)
            query_params: Optional filters (status, nextToken, maxResults)

        Returns:
            API response with controls list
        """
        status_filter = query_params.get("status")
        max_results = min(int(query_params.get("maxResults", 100)), 100)

        query_kwargs = {
            "KeyConditionExpression": Key("frameworkKey").eq(framework_key),
            "Limit": max_results,
        }

        if query_params.get("nextToken"):
            try:
                query_kwargs["ExclusiveStartKey"] = json.loads(
                    query_params["nextToken"]
                )
            except json.JSONDecodeError:
                return validation_error_response("Invalid nextToken format")

        response = self.table.query(**query_kwargs)
        items = response.get("Items", [])

        # Filter by status if provided
        if status_filter:
            items = [i for i in items if i.get("status") == status_filter]

        result = {
            "frameworkKey": framework_key,
            "controls": items,
            "count": len(items),
        }

        if response.get("LastEvaluatedKey"):
            result["nextToken"] = json.dumps(response["LastEvaluatedKey"])

        return success_response(result)

    def get_control(self, framework_key: str, control_id: str) -> Dict[str, Any]:
        """
        Get a specific control.

        Args:
            framework_key: Framework key (frameworkName#version)
            control_id: Control identifier

        Returns:
            API response with control details
        """
        control_key = f"{framework_key}#{control_id}"

        response = self.table.get_item(
            Key={"frameworkKey": framework_key, "controlKey": control_key}
        )

        item = response.get("Item")
        if not item:
            return not_found_response(
                "Control", f"{control_id} in framework {framework_key}"
            )

        return success_response(item)

    def create_or_update_control(
        self,
        framework_key: str,
        control_id: str,
        request: ControlCreateRequest,
    ) -> Dict[str, Any]:
        """
        Create or update a control.

        Args:
            framework_key: Framework key (frameworkName#version)
            control_id: Control identifier
            request: ControlCreateRequest model with control details

        Returns:
            API response with created/updated control
        """
        now = datetime.utcnow().isoformat()
        control_key = f"{framework_key}#{control_id}"

        # Check if control exists
        existing = self.table.get_item(
            Key={"frameworkKey": framework_key, "controlKey": control_key}
        ).get("Item")

        item = {
            "frameworkKey": framework_key,
            "controlKey": control_key,
            "controlId": control_id,
            "controlVersion": "1.0",
            "status": "ACTIVE",
            "title": request.title,
            "description": request.description or "",
            "controlGuide": request.control_guide or "",
            "additionalInfo": request.additional_info or {},
            "lastModifiedBy": {"system": "api"},
            "lastModifiedAt": now,
        }

        if existing:
            # Update - preserve createdBy and createdAt
            item["createdBy"] = existing.get("createdBy", {"system": "api"})
            item["createdAt"] = existing.get("createdAt", now)
            item["arn"] = existing.get("arn", f"arn:aws:nexus::control:{control_key}")
        else:
            # Create new
            item["createdBy"] = {"system": "api"}
            item["createdAt"] = now
            item["arn"] = f"arn:aws:nexus::control:{control_key}"

        self.table.put_item(Item=item)

        if existing:
            return success_response(item)
        else:
            return created_response(item)

    def batch_create_controls(
        self,
        framework_key: str,
        request: BatchControlsCreateRequest,
    ) -> Dict[str, Any]:
        """
        Bulk create controls (up to 100 per request).

        Args:
            framework_key: Framework key (frameworkName#version)
            request: BatchControlsCreateRequest model with controls to create

        Returns:
            API response with results
        """
        now = datetime.utcnow().isoformat()
        created: List[Dict[str, str]] = []
        errors: List[Dict[str, str]] = []

        with self.table.batch_writer() as batch:
            for ctrl in request.controls:
                control_key = f"{framework_key}#{ctrl.control_id}"

                item = {
                    "frameworkKey": framework_key,
                    "controlKey": control_key,
                    "controlId": ctrl.control_id,
                    "controlVersion": "1.0",
                    "status": "ACTIVE",
                    "title": ctrl.title,
                    "description": ctrl.description or "",
                    "controlGuide": ctrl.control_guide or "",
                    "additionalInfo": ctrl.additional_info or {},
                    "createdBy": {"system": "api"},
                    "createdAt": now,
                    "lastModifiedBy": {"system": "api"},
                    "lastModifiedAt": now,
                    "arn": f"arn:aws:nexus::control:{control_key}",
                }

                batch.put_item(Item=item)
                created.append({"controlId": ctrl.control_id, "controlKey": control_key})

        return accepted_response(
            {
                "frameworkKey": framework_key,
                "created": created,
                "createdCount": len(created),
                "errors": errors,
                "errorCount": len(errors),
            }
        )

    def archive_control(self, framework_key: str, control_id: str) -> Dict[str, Any]:
        """
        Archive a control (set status to ARCHIVED).

        Args:
            framework_key: Framework key (frameworkName#version)
            control_id: Control identifier

        Returns:
            API response confirming archive
        """
        control_key = f"{framework_key}#{control_id}"

        # Check if exists
        existing = self.table.get_item(
            Key={"frameworkKey": framework_key, "controlKey": control_key}
        ).get("Item")

        if not existing:
            return not_found_response("Control", control_id)

        if existing.get("status") == "ARCHIVED":
            return validation_error_response("Control is already archived")

        # Update status
        self.table.update_item(
            Key={"frameworkKey": framework_key, "controlKey": control_key},
            UpdateExpression="SET #status = :status, lastModifiedAt = :now",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "ARCHIVED",
                ":now": datetime.utcnow().isoformat(),
            },
        )

        return success_response(
            {
                "message": f"Control '{control_id}' archived",
                "controlKey": control_key,
                "status": "ARCHIVED",
            }
        )

    def batch_archive_controls(
        self,
        framework_key: str,
        request: BatchArchiveRequest,
    ) -> Dict[str, Any]:
        """
        Bulk archive controls (up to 100 per request).

        Args:
            framework_key: Framework key (frameworkName#version)
            request: BatchArchiveRequest model with control IDs to archive

        Returns:
            API response with results
        """
        now = datetime.utcnow().isoformat()
        archived = []
        errors = []

        for control_id in request.control_ids:
            control_key = f"{framework_key}#{control_id}"

            try:
                # Check if exists
                existing = self.table.get_item(
                    Key={"frameworkKey": framework_key, "controlKey": control_key}
                ).get("Item")

                if not existing:
                    errors.append({"controlId": control_id, "error": "Not found"})
                    continue

                if existing.get("status") == "ARCHIVED":
                    errors.append({"controlId": control_id, "error": "Already archived"})
                    continue

                self.table.update_item(
                    Key={"frameworkKey": framework_key, "controlKey": control_key},
                    UpdateExpression="SET #status = :status, lastModifiedAt = :now",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={":status": "ARCHIVED", ":now": now},
                )
                archived.append(control_id)

            except Exception as e:
                logger.error(f"Error archiving control {control_id}: {e}")
                errors.append({"controlId": control_id, "error": str(e)})

        return success_response(
            {
                "frameworkKey": framework_key,
                "archived": archived,
                "archivedCount": len(archived),
                "errors": errors,
                "errorCount": len(errors),
            }
        )
