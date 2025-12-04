"""Reasoning agent business logic.

Calls NexusStrandsAgentService to generate mapping reasoning.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import urllib3

logger = logging.getLogger(__name__)

STRANDS_SERVICE_ENDPOINT = os.environ.get("STRANDS_SERVICE_ENDPOINT", "")
REQUEST_TIMEOUT = 60.0  # 1 minute for reasoning generation


class ReasoningAgentService:
    """Service class for mapping reasoning operations."""

    def __init__(
        self,
        strands_endpoint: Optional[str] = None,
    ):
        """
        Initialize the reasoning agent service.

        Args:
            strands_endpoint: Optional strands service endpoint override.
        """
        self.strands_endpoint = strands_endpoint or STRANDS_SERVICE_ENDPOINT
        self.http = urllib3.PoolManager()

    def generate_reasoning(
        self,
        source_control_id: str,
        source_text: str,
        mapping: dict,
    ) -> Dict[str, Any]:
        """
        Generate reasoning for a control mapping.

        Args:
            source_control_id: Source control identifier.
            source_text: Source control text.
            mapping: Mapping dict with target control info and scores.

        Returns:
            Dict with reasoning text.

        Raises:
            RuntimeError: If strands service call fails.
        """
        # Extract target control info
        target_control_id = (
            mapping.get("target_control_id")
            or mapping.get("target_control_key")
            or "unknown"
        )
        target_framework = (
            mapping.get("target_framework")
            or mapping.get("target_framework_key", "").split("#")[0]
            or "Unknown"
        )
        target_text = mapping.get("text", "")
        similarity_score = mapping.get("similarity_score", 0.0)
        rerank_score = mapping.get("rerank_score", 0.0)

        # Call strands service
        reasoning_result = self._call_strands_reason(
            source_control_id=source_control_id,
            source_text=source_text,
            target_control_id=target_control_id,
            target_framework=target_framework,
            target_text=target_text,
            similarity_score=similarity_score,
            rerank_score=rerank_score,
        )

        return {
            "reasoning": reasoning_result.get("reasoning", ""),
            "source_control_id": source_control_id,
            "target_control_id": target_control_id,
        }

    def _call_strands_reason(
        self,
        source_control_id: str,
        source_text: str,
        target_control_id: str,
        target_framework: str,
        target_text: str,
        similarity_score: float,
        rerank_score: float,
    ) -> dict:
        """
        Call NexusStrandsAgentService /reason endpoint.

        Args:
            source_control_id: Source control identifier.
            source_text: Source control text.
            target_control_id: Target control identifier.
            target_framework: Target framework name.
            target_text: Target control text.
            similarity_score: Embedding similarity score.
            rerank_score: Cross-encoder rerank score.

        Returns:
            Reasoning response dict.

        Raises:
            RuntimeError: If API call fails.
        """
        if not self.strands_endpoint:
            logger.warning("STRANDS_SERVICE_ENDPOINT not configured, using mock reasoning")
            return self._mock_reason(
                source_control_id=source_control_id,
                source_text=source_text,
                target_control_id=target_control_id,
                target_framework=target_framework,
                target_text=target_text,
                similarity_score=similarity_score,
                rerank_score=rerank_score,
            )

        url = f"{self.strands_endpoint}/api/v1/reason"
        payload = {
            "sourceControlId": source_control_id,
            "sourceText": source_text,
            "mapping": {
                "targetControlId": target_control_id,
                "targetFramework": target_framework,
                "text": target_text,
                "similarityScore": similarity_score,
                "rerankScore": rerank_score,
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

    def _mock_reason(
        self,
        source_control_id: str,
        source_text: str,
        target_control_id: str,
        target_framework: str,
        target_text: str,
        similarity_score: float,
        rerank_score: float,
    ) -> dict:
        """
        Generate mock reasoning when strands service is unavailable.

        Args:
            source_control_id: Source control identifier.
            source_text: Source control text.
            target_control_id: Target control identifier.
            target_framework: Target framework name.
            target_text: Target control text.
            similarity_score: Embedding similarity score.
            rerank_score: Cross-encoder rerank score.

        Returns:
            Mock reasoning response.
        """
        # Generate a basic reasoning based on scores
        if rerank_score >= 0.8:
            strength = "strong"
        elif rerank_score >= 0.6:
            strength = "moderate"
        else:
            strength = "weak"

        reasoning = (
            f"This mapping shows a {strength} alignment between the AWS control "
            f"({source_control_id}) and the {target_framework} control ({target_control_id}). "
            f"Both controls address similar security objectives. "
            f"The semantic similarity score of {similarity_score:.2f} and relevance score of "
            f"{rerank_score:.2f} indicate that these controls share common compliance requirements."
        )

        return {
            "sourceControlId": source_control_id,
            "targetControlId": target_control_id,
            "reasoning": reasoning,
            "status": "success",
        }
