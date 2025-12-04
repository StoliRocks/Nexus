"""Mappings handler business logic."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

from nexus_application_commons.dynamodb.response_builder import (
    accepted_response,
    not_found_response,
    success_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import (
    BatchMappingsCreateRequest,
    Mapping,
    MappingStatus,
)

logger = logging.getLogger(__name__)

MAPPINGS_TABLE_NAME = os.environ.get("MAPPINGS_TABLE_NAME", "ControlMappings")
MAX_BATCH_SIZE = 100


class MappingService:
    """Service class for mapping CRUD operations."""

    def __init__(
        self, dynamodb_resource: Optional[Any] = None, table_name: Optional[str] = None
    ):
        """
        Initialize the mapping service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            table_name: Optional table name override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or MAPPINGS_TABLE_NAME
        self.table = self.dynamodb.Table(self.table_name)

    def list_mappings(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List mappings with optional filters.

        Args:
            query_params: Filters (status, frameworkName, frameworkVersion, nextToken, maxResults)

        Returns:
            API response with mappings list
        """
        status_filter = query_params.get("status")
        framework_name = query_params.get("frameworkName")
        framework_version = query_params.get("frameworkVersion")
        control_id = query_params.get("control")
        max_results = min(int(query_params.get("maxResults", 100)), 100)

        # Use StatusIndex if filtering by status
        if status_filter:
            query_kwargs = {
                "IndexName": "StatusIndex",
                "KeyConditionExpression": Key("status").eq(status_filter),
                "Limit": max_results,
                "ScanIndexForward": False,
            }
            if query_params.get("nextToken"):
                try:
                    query_kwargs["ExclusiveStartKey"] = json.loads(
                        query_params["nextToken"]
                    )
                except json.JSONDecodeError:
                    return validation_error_response("Invalid nextToken format")

            response = self.table.query(**query_kwargs)
        else:
            # Scan if no status filter
            scan_kwargs = {"Limit": max_results}
            if query_params.get("nextToken"):
                try:
                    scan_kwargs["ExclusiveStartKey"] = json.loads(
                        query_params["nextToken"]
                    )
                except json.JSONDecodeError:
                    return validation_error_response("Invalid nextToken format")

            response = self.table.scan(**scan_kwargs)

        items = response.get("Items", [])

        # Apply additional filters in memory
        if framework_name:
            framework_key_prefix = f"{framework_name}#"
            if framework_version:
                framework_key_prefix = f"{framework_name}#{framework_version}#"
            items = [
                i
                for i in items
                if i.get("controlKey", "").startswith(framework_key_prefix)
            ]

        if control_id:
            items = [i for i in items if control_id in i.get("controlKey", "")]

        result = {"mappings": items, "count": len(items)}

        if response.get("LastEvaluatedKey"):
            result["nextToken"] = json.dumps(response["LastEvaluatedKey"])

        return success_response(result)

    def get_mapping(self, mapping_id: str) -> Dict[str, Any]:
        """
        Get a specific mapping by mappingKey.

        Args:
            mapping_id: The mappingKey (sorted concatenation of controlKeys)

        Returns:
            API response with mapping details
        """
        # Query using MappingKeyIndex GSI
        response = self.table.query(
            IndexName="MappingKeyIndex",
            KeyConditionExpression=Key("mappingKey").eq(mapping_id),
        )

        items = response.get("Items", [])
        if not items:
            return not_found_response("Mapping", mapping_id)

        return success_response(items[0])

    def get_mappings_for_control(
        self, control_id: str, query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get all mappings for a specific control.

        Args:
            control_id: Control identifier (can be partial or full controlKey)
            query_params: Filters (status, framework, nextToken, maxResults)

        Returns:
            API response with mappings list
        """
        status_filter = query_params.get("status")
        framework_filter = query_params.get("framework")
        max_results = min(int(query_params.get("maxResults", 100)), 100)

        # Use ControlStatusIndex if we have status filter
        if status_filter:
            query_kwargs = {
                "IndexName": "ControlStatusIndex",
                "KeyConditionExpression": Key("controlKey").eq(control_id)
                & Key("status").eq(status_filter),
                "Limit": max_results,
            }
        else:
            # Query by controlKey (primary key)
            query_kwargs = {
                "KeyConditionExpression": Key("controlKey").eq(control_id),
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

        # Filter by target framework if specified
        if framework_filter:
            items = [
                i for i in items if framework_filter in i.get("mappedControlKey", "")
            ]

        result = {
            "controlId": control_id,
            "mappings": items,
            "count": len(items),
        }

        if response.get("LastEvaluatedKey"):
            result["nextToken"] = json.dumps(response["LastEvaluatedKey"])

        return success_response(result)

    def batch_create_mappings(
        self, request: BatchMappingsCreateRequest
    ) -> Dict[str, Any]:
        """
        Bulk create mappings (up to 100 per request).

        Args:
            request: BatchMappingsCreateRequest model with mappings to create

        Returns:
            API response with results
        """
        now = datetime.utcnow().isoformat()
        created: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        with self.table.batch_writer() as batch:
            for mapping_request in request.mappings:
                # Generate mappingKey using Mapping utility (sorted concatenation)
                mapping_key = Mapping.generate_mapping_key(
                    mapping_request.source_control_key,
                    mapping_request.target_control_key,
                )

                # Build item dict directly to avoid ARN validation issues
                # in the Mapping model (ARN validator doesn't handle # in keys)
                item: Dict[str, Any] = {
                    "controlKey": mapping_request.source_control_key,
                    "mappedControlKey": mapping_request.target_control_key,
                    "mappingKey": mapping_key,
                    "status": MappingStatus.APPROVED.value,
                    "mappingWorkflowKey": "manual",
                    "timestamp": now,
                    "arn": f"arn:aws:nexus:::mapping/{mapping_key}",
                    "createdBy": {"type": "API", "timestamp": now},
                    "lastModifiedBy": {"type": "API", "timestamp": now},
                }

                batch.put_item(Item=item)
                created.append(
                    {
                        "mappingKey": mapping_key,
                        "sourceControlKey": mapping_request.source_control_key,
                        "targetControlKey": mapping_request.target_control_key,
                    }
                )

        return accepted_response(
            {
                "created": created,
                "createdCount": len(created),
                "errors": errors,
                "errorCount": len(errors),
            }
        )

    def archive_mapping(self, mapping_id: str) -> Dict[str, Any]:
        """
        Archive a mapping (set status to ARCHIVED).

        Args:
            mapping_id: The mappingKey

        Returns:
            API response confirming archive
        """
        # First find the mapping using MappingKeyIndex
        response = self.table.query(
            IndexName="MappingKeyIndex",
            KeyConditionExpression=Key("mappingKey").eq(mapping_id),
        )

        items = response.get("Items", [])
        if not items:
            return not_found_response("Mapping", mapping_id)

        item = items[0]
        control_key = item["controlKey"]
        mapped_control_key = item["mappedControlKey"]

        if item.get("status") == "ARCHIVED":
            return validation_error_response("Mapping is already archived")

        # Update status using the actual primary key
        self.table.update_item(
            Key={"controlKey": control_key, "mappedControlKey": mapped_control_key},
            UpdateExpression="SET #status = :status, #ts = :now",
            ExpressionAttributeNames={"#status": "status", "#ts": "timestamp"},
            ExpressionAttributeValues={
                ":status": "ARCHIVED",
                ":now": datetime.utcnow().isoformat(),
            },
        )

        return success_response(
            {
                "message": f"Mapping '{mapping_id}' archived",
                "mappingKey": mapping_id,
                "status": "ARCHIVED",
            }
        )
