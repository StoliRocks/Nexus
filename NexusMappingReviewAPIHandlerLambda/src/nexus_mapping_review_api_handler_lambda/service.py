"""Reviews handler business logic."""

import json
import logging
import os
import uuid
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
from nexus_application_interface.api.v1 import ReviewCreateRequest, ReviewUpdateRequest

logger = logging.getLogger(__name__)

REVIEWS_TABLE_NAME = os.environ.get("REVIEWS_TABLE_NAME", "MappingReviews")


class ReviewService:
    """Service class for review CRUD operations."""

    def __init__(
        self, dynamodb_resource: Optional[Any] = None, table_name: Optional[str] = None
    ):
        """
        Initialize the review service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing)
            table_name: Optional table name override
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or REVIEWS_TABLE_NAME
        self.table = self.dynamodb.Table(self.table_name)

    def list_reviews(
        self, mapping_id: str, query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        List all reviews for a mapping.

        Args:
            mapping_id: The mappingKey
            query_params: Pagination parameters (nextToken, maxResults)

        Returns:
            API response with reviews list
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
            "reviews": items,
            "count": len(items),
        }

        if response.get("LastEvaluatedKey"):
            result["nextToken"] = json.dumps(response["LastEvaluatedKey"])

        return success_response(result)

    def create_review(
        self, mapping_id: str, request: ReviewCreateRequest
    ) -> Dict[str, Any]:
        """
        Create a new review for a mapping.

        Args:
            mapping_id: The mappingKey
            request: ReviewCreateRequest model with review data

        Returns:
            API response with created review
        """
        now = datetime.utcnow().isoformat()
        review_id = str(uuid.uuid4())
        review_key = f"{request.reviewer_id}#{review_id}"

        item = {
            "mappingKey": mapping_id,
            "reviewKey": review_key,
            "reviewId": review_id,
            "reviewerId": request.reviewer_id,
            "correct": request.correct,
            "isFinalReview": request.is_final_review,
            "feedback": request.feedback or {},
            "submittedAt": now,
            "submittedBy": {"system": "api"},
        }

        self.table.put_item(Item=item)

        return created_response(
            {
                "message": "Review submitted successfully",
                "mappingKey": mapping_id,
                "reviewId": review_id,
                "reviewKey": review_key,
            }
        )

    def update_review(
        self,
        mapping_id: str,
        review_id: str,
        request: ReviewUpdateRequest,
    ) -> Dict[str, Any]:
        """
        Update an existing review.

        Args:
            mapping_id: The mappingKey
            review_id: The reviewId (or full reviewKey)
            request: ReviewUpdateRequest model with updated data

        Returns:
            API response confirming update
        """
        # Find the review - reviewId might be just the UUID or full reviewKey
        response = self.table.query(
            KeyConditionExpression=Key("mappingKey").eq(mapping_id),
        )

        items = response.get("Items", [])
        matching = [
            i
            for i in items
            if i.get("reviewId") == review_id or i.get("reviewKey") == review_id
        ]

        if not matching:
            return not_found_response(
                "Review", f"{review_id} for mapping {mapping_id}"
            )

        existing = matching[0]
        review_key = existing["reviewKey"]

        if not request.has_updates():
            return validation_error_response("No fields to update")

        # Build update expression
        update_parts: list[str] = []
        expr_values: Dict[str, Any] = {}
        expr_names: Dict[str, str] = {}

        if request.correct is not None:
            update_parts.append("#correct = :correct")
            expr_names["#correct"] = "correct"
            expr_values[":correct"] = request.correct

        if request.feedback is not None:
            update_parts.append("#feedback = :feedback")
            expr_names["#feedback"] = "feedback"
            expr_values[":feedback"] = request.feedback

        if request.is_final_review is not None:
            update_parts.append("#isFinal = :isFinal")
            expr_names["#isFinal"] = "isFinalReview"
            expr_values[":isFinal"] = request.is_final_review

        # Always update timestamp
        update_parts.append("#updated = :updated")
        expr_names["#updated"] = "updatedAt"
        expr_values[":updated"] = datetime.utcnow().isoformat()

        self.table.update_item(
            Key={"mappingKey": mapping_id, "reviewKey": review_key},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

        return success_response(
            {
                "message": "Review updated successfully",
                "mappingKey": mapping_id,
                "reviewId": review_id,
                "reviewKey": review_key,
            }
        )
