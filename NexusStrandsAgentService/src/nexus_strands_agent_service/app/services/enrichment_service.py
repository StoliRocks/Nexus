"""Enrichment service - wraps NexusEnrichmentAgent for HTTP API."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from nexus_strands_agent_service.app.config import get_settings

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Service layer for control enrichment via multi-agent system.

    Wraps NexusEnrichmentAgent processors for HTTP API consumption.
    """

    def __init__(self):
        """Initialize the enrichment service."""
        self.settings = get_settings()
        self._processor_cache: Dict[str, Any] = {}

    def _get_session_params(self) -> Optional[Dict[str, Any]]:
        """Get Bedrock session parameters for cross-account access."""
        if not self.settings.bedrock_role_arn:
            return None

        return {
            "role_arn": self.settings.bedrock_role_arn,
            "external_id": self.settings.bedrock_external_id,
            "region_name": self.settings.aws_region,
        }

    def _get_processor(
        self, framework_name: str, framework_profile: Optional[Dict[str, Any]] = None
    ):
        """
        Get or create a processor for the given framework.

        Processors are cached by framework name to avoid recreation overhead.
        """
        # Import here to avoid circular dependencies and allow service to start
        # even if NexusEnrichmentAgent isn't installed (for testing)
        try:
            from nexus_enrichment_agent import ProfileDrivenMultiAgentProcessor
        except ImportError:
            logger.error("NexusEnrichmentAgent not installed")
            raise ImportError(
                "NexusEnrichmentAgent package is required but not installed. "
                "Install it with: pip install nexus-enrichment-agent"
            )

        cache_key = framework_name
        if cache_key not in self._processor_cache or framework_profile:
            # Create new processor with optional profile
            self._processor_cache[cache_key] = ProfileDrivenMultiAgentProcessor(
                framework_name=framework_name,
                framework_profile=framework_profile,
                model=self.settings.bedrock_model_id,
                session_params=self._get_session_params(),
            )

        return self._processor_cache[cache_key]

    async def enrich_control(
        self,
        metadata: Dict[str, Any],
        control: Dict[str, Any],
        framework_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich a single control using the multi-agent system.

        Args:
            metadata: Framework metadata (frameworkName, frameworkVersion)
            control: Control data (shortId, title, description, supplementalGuidance)
            framework_profile: Optional pre-generated framework profile

        Returns:
            Dict with enriched_interpretation, agent_outputs, status
        """
        framework_name = metadata.get("frameworkName", "Unknown")

        try:
            processor = self._get_processor(framework_name, framework_profile)

            # Run the synchronous processor in a thread pool
            result = await asyncio.to_thread(
                processor.interpret_control_intent,
                metadata,
                control,
            )

            # Parse the enriched interpretation if it's a string
            enriched = result.get("enriched_interpretation", "")
            if isinstance(enriched, str):
                try:
                    # Try to parse as JSON
                    enriched = json.loads(enriched)
                except json.JSONDecodeError:
                    # Keep as string if not valid JSON
                    enriched = {"raw_interpretation": enriched}

            return {
                "enriched_interpretation": enriched,
                "agent_outputs": result.get("agent_outputs"),
                "framework_profile_applied": result.get("framework_profile_applied"),
                "status": result.get("status", "success"),
            }

        except Exception as e:
            logger.error(f"Enrichment failed for {control.get('shortId')}: {e}")
            return {
                "enriched_interpretation": {"error": str(e)},
                "status": "failed",
            }

    async def generate_framework_profile(
        self,
        framework_name: str,
        sample_controls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a framework profile from sample controls.

        Args:
            framework_name: Name of the framework
            sample_controls: List of sample controls (3-5 recommended)

        Returns:
            Generated framework profile dict
        """
        try:
            from nexus_enrichment_agent import DynamicFrameworkProfileGenerator
        except ImportError:
            logger.error("NexusEnrichmentAgent not installed")
            raise ImportError(
                "NexusEnrichmentAgent package is required but not installed."
            )

        try:
            # Create profile generator
            generator = DynamicFrameworkProfileGenerator(
                framework_name=framework_name,
                model=self.settings.bedrock_model_id,
                session_params=self._get_session_params(),
            )

            # Generate profile (async method)
            profile = await generator.generate_profile(sample_controls)

            return profile

        except Exception as e:
            logger.error(f"Profile generation failed for {framework_name}: {e}")
            raise
