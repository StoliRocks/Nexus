"""NexusMappingAPIHandlerLambda - CRUD operations for control mappings.

This Lambda handles mapping management operations:
- List mappings with filters
- Get a specific mapping
- Get mappings for a control
- Batch create mappings
- Archive mappings
"""

from nexus_mapping_api_handler_lambda.handler import lambda_handler, api_endpoint_handler
from nexus_mapping_api_handler_lambda.service import MappingService

__all__ = [
    "lambda_handler",
    "api_endpoint_handler",
    "MappingService",
]
