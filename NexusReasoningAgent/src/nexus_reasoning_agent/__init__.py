"""NexusReasoningAgent - Generates human-readable rationale for control mappings.

This package provides reasoning generation for explaining why AWS controls
map to framework controls using Claude via Bedrock.
"""

from nexus_reasoning_agent.reasoning_generator import (
    ReasoningGenerator,
    generate_reasoning,
)
from nexus_reasoning_agent.prompts import (
    build_mapping_rationale_prompt,
    build_batch_reasoning_prompt,
)

__all__ = [
    "ReasoningGenerator",
    "generate_reasoning",
    "build_mapping_rationale_prompt",
    "build_batch_reasoning_prompt",
]
