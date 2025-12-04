"""Enrichment Agent Lambda - enriches control text via NexusStrandsAgentService."""

from typing import Any

from nexus_enrichment_agent_lambda.service import EnrichmentAgentService


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Enrich control text and store in DynamoDB.

    Args:
        event: Dict with control_key and control (title, description, metadata).
        context: Lambda context (unused).

    Returns:
        Dict with control_key, enriched_text, status.
    """
    service = EnrichmentAgentService()

    control_key = event.get("control_key")
    if not control_key:
        return {
            "control_key": None,
            "error": "control_key is required",
            "status": "error",
        }

    control = event.get("control", {})

    try:
        result = service.enrich_control(control_key, control)
        return {
            "control_key": control_key,
            "enriched_text": result.get("enriched_text", ""),
            "status": "success",
        }
    except Exception as e:
        return {
            "control_key": control_key,
            "error": str(e),
            "status": "error",
        }


# Alias for BATS Lambda configuration
api_endpoint_handler = lambda_handler
