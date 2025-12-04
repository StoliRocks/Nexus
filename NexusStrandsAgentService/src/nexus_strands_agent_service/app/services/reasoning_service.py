"""Reasoning service - wraps NexusReasoningAgent for HTTP API."""

import asyncio
import logging
from typing import Any, Dict, List

from nexus_strands_agent_service.app.config import get_settings

logger = logging.getLogger(__name__)


class ReasoningService:
    """
    Service layer for mapping reasoning generation.

    Wraps NexusReasoningAgent for HTTP API consumption.
    """

    def __init__(self):
        """Initialize the reasoning service."""
        self.settings = get_settings()
        self._generator = None

    def _get_generator(self):
        """
        Get or create the reasoning generator.

        Lazy initialization to avoid import issues at startup.
        """
        if self._generator is None:
            try:
                from nexus_reasoning_agent import ReasoningGenerator
            except ImportError:
                logger.error("NexusReasoningAgent not installed")
                raise ImportError(
                    "NexusReasoningAgent package is required but not installed. "
                    "Install it with: pip install nexus-reasoning-agent"
                )

            self._generator = ReasoningGenerator(
                model_id=self.settings.reasoning_model_id,
            )

        return self._generator

    async def generate_reasoning(
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
        """
        generator = self._get_generator()

        # Run the synchronous generator in a thread pool
        reasoning = await asyncio.to_thread(
            generator.generate_reasoning,
            source_control_id,
            source_text,
            mapping,
        )

        return reasoning

    async def generate_batch_reasoning(
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
            List of dicts with control_id, reasoning, source_control_id, status
        """
        generator = self._get_generator()

        # Run the synchronous generator in a thread pool
        results = await asyncio.to_thread(
            generator.generate_batch_reasoning,
            source_control_id,
            source_text,
            mappings,
        )

        return results

    async def generate_consolidated_reasoning(
        self,
        source_control_id: str,
        source_text: str,
        mappings: List[Dict[str, Any]],
    ) -> str:
        """
        Generate consolidated reasoning for all mappings in a single API call.

        More efficient for multiple mappings as it uses a single Bedrock API call.

        Args:
            source_control_id: AWS control identifier
            source_text: AWS control description text
            mappings: List of mapping dicts

        Returns:
            Consolidated reasoning string
        """
        generator = self._get_generator()

        # Run the synchronous generator in a thread pool
        consolidated = await asyncio.to_thread(
            generator.generate_consolidated_reasoning,
            source_control_id,
            source_text,
            mappings,
        )

        return consolidated
