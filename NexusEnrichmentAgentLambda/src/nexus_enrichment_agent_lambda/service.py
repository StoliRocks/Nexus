"""Enrichment agent business logic.

Calls NexusStrandsAgentService to enrich control text using multi-agent system.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
import urllib3

logger = logging.getLogger(__name__)

ENRICHMENT_TABLE_NAME = os.environ.get("ENRICHMENT_TABLE_NAME", "Enrichment")
STRANDS_SERVICE_ENDPOINT = os.environ.get("STRANDS_SERVICE_ENDPOINT", "")
ENRICHMENT_VERSION = os.environ.get("ENRICHMENT_VERSION", "v1")
REQUEST_TIMEOUT = 120.0  # 2 minutes for agent processing


class EnrichmentAgentService:
    """Service class for control enrichment operations."""

    def __init__(
        self,
        dynamodb_resource: Any = None,
        enrichment_table_name: Optional[str] = None,
        strands_endpoint: Optional[str] = None,
    ):
        """
        Initialize the enrichment agent service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing).
            enrichment_table_name: Optional table name override.
            strands_endpoint: Optional strands service endpoint override.
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.enrichment_table_name = enrichment_table_name or ENRICHMENT_TABLE_NAME
        self.enrichment_table = self.dynamodb.Table(self.enrichment_table_name)
        self.strands_endpoint = strands_endpoint or STRANDS_SERVICE_ENDPOINT
        self.http = urllib3.PoolManager()

    def enrich_control(self, control_key: str, control: dict) -> Dict[str, Any]:
        """
        Enrich control text using NexusStrandsAgentService.

        Args:
            control_key: Full control key (frameworkKey#controlId).
            control: Control data dict with title, description, metadata.

        Returns:
            Dict with enriched_text and metadata.

        Raises:
            RuntimeError: If strands service call fails.
        """
        # Extract control text from various possible fields
        control_text = (
            control.get("description")
            or control.get("text")
            or control.get("title", "")
        )

        # Parse control_key to extract components
        framework_name, framework_version, control_id = self._parse_control_key(control_key)

        # Get metadata or build from control_key
        metadata = control.get("metadata", {})
        if not metadata.get("frameworkName"):
            metadata["frameworkName"] = framework_name
        if not metadata.get("frameworkVersion"):
            metadata["frameworkVersion"] = framework_version

        # Call strands service
        enrichment_result = self._call_strands_enrich(
            control_id=control_id,
            title=control.get("title", ""),
            description=control_text,
            metadata=metadata,
        )

        # Extract enriched text from response
        enriched_interpretation = enrichment_result.get("enrichedInterpretation", {})
        enriched_text = (
            enriched_interpretation.get("enrichedText")
            or enriched_interpretation.get("summary")
            or control_text  # Fallback to original
        )

        # Store enrichment in DynamoDB
        self._store_enrichment(
            control_key=control_key,
            original_text=control_text,
            enriched_text=enriched_text,
            enrichment_data=enriched_interpretation,
        )

        return {
            "enriched_text": enriched_text,
            "enrichment_data": enriched_interpretation,
        }

    def _parse_control_key(self, control_key: str) -> tuple:
        """
        Parse controlKey into components.

        Args:
            control_key: Full control key (frameworkName#version#controlId).

        Returns:
            Tuple of (frameworkName, version, controlId).
        """
        parts = control_key.split("#")
        if len(parts) >= 3:
            return parts[0], parts[1], "#".join(parts[2:])
        elif len(parts) == 2:
            return parts[0], "1.0", parts[1]
        else:
            return "Unknown", "1.0", control_key

    def _call_strands_enrich(
        self,
        control_id: str,
        title: str,
        description: str,
        metadata: dict,
    ) -> dict:
        """
        Call NexusStrandsAgentService /enrich endpoint.

        Args:
            control_id: Control identifier.
            title: Control title.
            description: Control description text.
            metadata: Framework metadata dict.

        Returns:
            Enrichment response dict.

        Raises:
            RuntimeError: If API call fails.
        """
        if not self.strands_endpoint:
            logger.warning("STRANDS_SERVICE_ENDPOINT not configured, using mock enrichment")
            return self._mock_enrich(control_id, title, description)

        url = f"{self.strands_endpoint}/api/v1/enrich"
        payload = {
            "metadata": {
                "frameworkName": metadata.get("frameworkName", "Unknown"),
                "frameworkVersion": metadata.get("frameworkVersion", "1.0"),
            },
            "control": {
                "shortId": control_id,
                "title": title,
                "description": description,
            },
        }

        try:
            response = self.http.request(
                "POST",
                url,
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )

            if response.status != 200:
                raise RuntimeError(
                    f"Strands service error: {response.status} - {response.data.decode('utf-8')}"
                )

            return json.loads(response.data.decode("utf-8"))

        except urllib3.exceptions.TimeoutError:
            raise RuntimeError("Strands service timeout")
        except Exception as e:
            raise RuntimeError(f"Strands service call failed: {str(e)}")

    def _mock_enrich(self, control_id: str, title: str, description: str) -> dict:
        """
        Generate mock enrichment when strands service is unavailable.

        Args:
            control_id: Control identifier.
            title: Control title.
            description: Control description.

        Returns:
            Mock enrichment response.
        """
        enriched_text = f"{description} This control ensures compliance with security best practices and regulatory requirements."

        return {
            "controlId": control_id,
            "enrichedInterpretation": {
                "enrichedText": enriched_text,
                "securityObjective": f"Ensure {title.lower()} is properly configured.",
                "complianceContext": "Relevant to access control and security monitoring requirements.",
            },
            "status": "success",
        }

    def _store_enrichment(
        self,
        control_key: str,
        original_text: str,
        enriched_text: str,
        enrichment_data: dict,
    ) -> None:
        """
        Store enrichment result in DynamoDB.

        Args:
            control_key: Full control key.
            original_text: Original control text.
            enriched_text: Enriched control text.
            enrichment_data: Full enrichment interpretation data.
        """
        self.enrichment_table.put_item(
            Item={
                "control_id": control_key,
                "enriched_text": enriched_text,
                "original_text": original_text,
                "enrichment_data": enrichment_data,
                "enrichment_version": ENRICHMENT_VERSION,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
