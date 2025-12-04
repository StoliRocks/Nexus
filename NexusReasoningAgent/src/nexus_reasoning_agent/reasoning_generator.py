"""Reasoning generator for control mapping rationale."""

import json
import logging
import os
from typing import Dict, Any, Optional, List

import boto3
from botocore.exceptions import ClientError

from nexus_reasoning_agent.prompts import (
    build_mapping_rationale_prompt,
    build_batch_reasoning_prompt,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


class ReasoningGenerator:
    """
    Generates human-readable rationale for control mappings using Claude.

    Supports both single mapping reasoning and batch processing.
    """

    def __init__(
        self,
        model_id: str = None,
        bedrock_client=None,
        max_tokens: int = 300,
        temperature: float = 0.0,
    ):
        """
        Initialize the reasoning generator.

        Args:
            model_id: Bedrock model ID (default: claude-3-haiku)
            bedrock_client: Optional pre-configured Bedrock client
            max_tokens: Maximum response tokens
            temperature: Model temperature (0.0 for deterministic)
        """
        self.model_id = model_id or os.environ.get("REASONING_MODEL_ID", DEFAULT_MODEL_ID)
        self.bedrock = bedrock_client or boto3.client("bedrock-runtime")
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate_reasoning(
        self,
        source_control_id: str,
        source_text: str,
        mapping: Dict[str, Any],
    ) -> str:
        """
        Generate human-readable rationale for a control mapping.

        Args:
            source_control_id: AWS control identifier
            source_text: AWS control description text
            mapping: Dict with target_control_id, target_framework, scores, text

        Returns:
            Reasoning explanation string

        Raises:
            ClientError: If Bedrock invocation fails
        """
        prompt = build_mapping_rationale_prompt(
            source_control_id=source_control_id,
            source_text=source_text,
            target_control_id=mapping["target_control_id"],
            target_framework=mapping["target_framework"],
            target_text=mapping.get("text", ""),
            similarity_score=mapping.get("similarity_score", 0.0),
            rerank_score=mapping.get("rerank_score", 0.0),
        )

        return self._call_claude(prompt)

    def generate_batch_reasoning(
        self,
        source_control_id: str,
        source_text: str,
        mappings: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate reasoning for multiple mappings.

        Args:
            source_control_id: AWS control identifier
            source_text: AWS control description text
            mappings: List of mapping dicts

        Returns:
            List of dicts with control_id, reasoning, source_control_id
        """
        results = []

        for mapping in mappings:
            try:
                reasoning = self.generate_reasoning(
                    source_control_id=source_control_id,
                    source_text=source_text,
                    mapping=mapping,
                )
                results.append({
                    "control_id": mapping["target_control_id"],
                    "reasoning": reasoning,
                    "source_control_id": source_control_id,
                    "status": "success",
                })
            except Exception as e:
                logger.error(f"Reasoning failed for {mapping['target_control_id']}: {e}")
                results.append({
                    "control_id": mapping["target_control_id"],
                    "reasoning": f"Reasoning generation failed: {str(e)}",
                    "source_control_id": source_control_id,
                    "status": "failed",
                })

        return results

    def generate_consolidated_reasoning(
        self,
        source_control_id: str,
        source_text: str,
        mappings: List[Dict[str, Any]],
    ) -> str:
        """
        Generate consolidated reasoning for all mappings in a single prompt.

        More efficient for multiple mappings as it uses a single API call.

        Args:
            source_control_id: AWS control identifier
            source_text: AWS control description text
            mappings: List of mapping dicts

        Returns:
            Consolidated reasoning string
        """
        prompt = build_batch_reasoning_prompt(
            source_control_id=source_control_id,
            source_text=source_text,
            mappings=mappings,
        )

        return self._call_claude(prompt, max_tokens=self.max_tokens * len(mappings))

    def _call_claude(self, prompt: str, max_tokens: int = None) -> str:
        """
        Call Claude via Bedrock.

        Args:
            prompt: User prompt string
            max_tokens: Override default max_tokens

        Returns:
            Claude response text

        Raises:
            ClientError: If Bedrock invocation fails
        """
        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens or self.max_tokens,
                    "temperature": self.temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }),
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"].strip()

        except ClientError as e:
            logger.error(f"Bedrock invocation failed: {e}")
            raise


def generate_reasoning(
    source_control_id: str,
    source_text: str,
    mapping: Dict[str, Any],
    model_id: str = None,
) -> str:
    """
    Convenience function to generate reasoning without instantiating a class.

    Args:
        source_control_id: AWS control identifier
        source_text: AWS control description text
        mapping: Dict with target_control_id, target_framework, scores, text
        model_id: Optional Bedrock model ID

    Returns:
        Reasoning explanation string
    """
    generator = ReasoningGenerator(model_id=model_id)
    return generator.generate_reasoning(
        source_control_id=source_control_id,
        source_text=source_text,
        mapping=mapping,
    )
