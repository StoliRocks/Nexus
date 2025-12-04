"""Feedback handler business logic."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key

from nexus_application_commons.dynamodb.response_builder import (
    success_response,
    created_response,
    not_found_response,
    validation_error_response,
)
from nexus_application_interface.api.v1 import FeedbackCreateRequest, FeedbackUpdateRequest

logger = logging.getLogger(__name__)

FEEDBACKS_TABLE_NAME = os.environ.get("FEEDBACKS_TABLE_NAME", "MappingFeedbacks")


class FeedbackService:
    """Service class for feedback CRUD operations."""

    def __init__(
        self, dynamodb_resource: Optional[Any] = None, table_name: Optional[str] = None
    ):
        """
        Initialize the feedback service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            table_name: Optional table name override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or FEEDBACKS_TABLE_NAME
        self.table = self.dynamodb.Table(self.table_name)

    def list_feedbacks(
        self, mapping_id: str, query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        List all feedbacks for a mapping.

        Args:
            mapping_id: The mappingKey
            query_params: Pagination parameters (nextToken, maxResults)

        Returns:
            API response with feedbacks list
        """
        max_results = min(int(query_params.get("maxResults", 50)), 100)

        query_kwargs = {
            "KeyConditionExpression": Key("mappingKey").eq(mapping_id),
            "Limit": max_results,
            "ScanIndexForward": False,  # Most recent first
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

        result = {
            "mappingKey": mapping_id,
            "feedbacks": items,
            "count": len(items),
        }

        if response.get("LastEvaluatedKey"):
            result["nextToken"] = json.dumps(response["LastEvaluatedKey"])

        return success_response(result)

    def create_feedback(
        self, mapping_id: str, request: FeedbackCreateRequest
    ) -> Dict[str, Any]:
        """
        Create a new feedback for a mapping.

        Args:
            mapping_id: The mappingKey
            request: FeedbackCreateRequest model with feedback data

        Returns:
            API response with created feedback
        """
        now = datetime.utcnow().isoformat()
        # Use feedbackProviderId as reviewerId (sort key)
        reviewer_id = request.feedback_provider_id

        # Check if feedback already exists from this user
        existing = self.table.get_item(
            Key={"mappingKey": mapping_id, "reviewerId": reviewer_id}
        ).get("Item")

        if existing:
            return validation_error_response(
                f"Feedback already exists from user '{request.feedback_provider_id}'. "
                "Use PUT to update."
            )

        item: Dict[str, Any] = {
            "mappingKey": mapping_id,
            "reviewerId": reviewer_id,
            "feedbackProviderId": request.feedback_provider_id,
            "label": request.label,
            "decision": request.decision,
            "submittedAt": now,
            "submittedBy": {"system": "api"},
        }

        if request.feedback:
            item["feedback"] = request.feedback

        self.table.put_item(Item=item)

        return created_response(
            {
                "message": "Feedback submitted successfully",
                "mappingKey": mapping_id,
                "feedbackId": reviewer_id,
                "label": request.label,
            }
        )

    def update_feedback(
        self,
        mapping_id: str,
        feedback_id: str,
        request: FeedbackUpdateRequest,
    ) -> Dict[str, Any]:
        """
        Update an existing feedback.

        Args:
            mapping_id: The mappingKey
            feedback_id: The feedbackId (reviewerId)
            request: FeedbackUpdateRequest model with updated data

        Returns:
            API response confirming update
        """
        # Find the feedback
        existing = self.table.get_item(
            Key={"mappingKey": mapping_id, "reviewerId": feedback_id}
        ).get("Item")

        if not existing:
            return not_found_response(
                "Feedback", f"{feedback_id} for mapping {mapping_id}"
            )

        if not request.has_updates():
            return validation_error_response("No fields to update")

        now = datetime.utcnow().isoformat()

        # Build update expression
        update_parts: list[str] = []
        expr_values: Dict[str, Any] = {}
        expr_names: Dict[str, str] = {}

        # Track edit history if label is changing
        if request.label and request.label != existing.get("label"):
            # Add to edit history
            edit_entry = {
                "previousLabel": existing.get("label"),
                "previousFeedback": existing.get("feedback", {}),
                "editedAt": now,
            }
            edit_history = existing.get("editHistory", [])
            edit_history.append(edit_entry)

            update_parts.append("#label = :label")
            expr_names["#label"] = "label"
            expr_values[":label"] = request.label

            update_parts.append("#decision = :decision")
            expr_names["#decision"] = "decision"
            expr_values[":decision"] = request.decision

            update_parts.append("#editHistory = :editHistory")
            expr_names["#editHistory"] = "editHistory"
            expr_values[":editHistory"] = edit_history

        if request.feedback is not None:
            update_parts.append("#feedback = :feedback")
            expr_names["#feedback"] = "feedback"
            expr_values[":feedback"] = request.feedback

        # Always update timestamp
        update_parts.append("#updated = :updated")
        expr_names["#updated"] = "updatedAt"
        expr_values[":updated"] = now

        if len(update_parts) <= 1:  # Only timestamp
            return validation_error_response("No fields to update")

        self.table.update_item(
            Key={"mappingKey": mapping_id, "reviewerId": feedback_id},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

        return success_response(
            {
                "message": "Feedback updated successfully",
                "mappingKey": mapping_id,
                "feedbackId": feedback_id,
            }
        )
