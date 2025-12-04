"""Science Orchestrator Lambda - ML pipeline orchestration for control mapping.

Handles Step Functions actions: validate_control, check_enrichment, map_control.
"""

from typing import Any

from nexus_science_orchestrator_lambda.service import ScienceOrchestratorService


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Route to appropriate action handler.

    Args:
        event: Step Functions input with action and control parameters.
        context: Lambda context (unused).

    Returns:
        Action result dict.

    Raises:
        ValueError: Unknown action specified.
    """
    service = ScienceOrchestratorService()

    action = event.get("action")

    handlers = {
        "validate_control": service.validate_control,
        "check_enrichment": service.check_enrichment,
        "map_control": service.map_control,
    }

    handler = handlers.get(action)
    if not handler:
        raise ValueError(f"Unknown action: {action}")

    return handler(event)


# Alias for BATS Lambda configuration
api_endpoint_handler = lambda_handler
