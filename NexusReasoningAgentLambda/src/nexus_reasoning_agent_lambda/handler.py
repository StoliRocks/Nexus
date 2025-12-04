"""Reasoning Agent Lambda - generates mapping rationale via NexusStrandsAgentService."""

from typing import Any

from nexus_reasoning_agent_lambda.service import ReasoningAgentService


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Generate reasoning for a control mapping.

    Args:
        event: Dict with source_control_id, source_text, mapping.
        context: Lambda context (unused).

    Returns:
        Dict with control_id, reasoning, source_control_id, status.
    """
    service = ReasoningAgentService()

    source_control_id = event.get("source_control_id")
    mapping = event.get("mapping", {})
    source_text = event.get("source_text", "")

    target_control_id = (
        mapping.get("target_control_id")
        or mapping.get("target_control_key")
        or "unknown"
    )

    if not source_control_id:
        return {
            "control_id": target_control_id,
            "error": "source_control_id is required",
            "source_control_id": None,
            "status": "error",
        }

    if not mapping:
        return {
            "control_id": target_control_id,
            "error": "mapping is required",
            "source_control_id": source_control_id,
            "status": "error",
        }

    try:
        result = service.generate_reasoning(
            source_control_id=source_control_id,
            source_text=source_text,
            mapping=mapping,
        )
        return {
            "control_id": target_control_id,
            "reasoning": result.get("reasoning", ""),
            "source_control_id": source_control_id,
            "status": "success",
        }
    except Exception as e:
        return {
            "control_id": target_control_id,
            "error": str(e),
            "source_control_id": source_control_id,
            "status": "error",
        }


# Alias for BATS Lambda configuration
api_endpoint_handler = lambda_handler
