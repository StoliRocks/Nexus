"""NexusFrameworkAPIHandlerLambda - CRUD operations for compliance frameworks.

This Lambda handles framework management operations:
- List all frameworks
- List versions of a framework
- Get a specific framework version
- Create or update frameworks
- Archive frameworks
"""

from nexus_framework_api_handler_lambda.handler import lambda_handler, api_endpoint_handler
from nexus_framework_api_handler_lambda.service import FrameworkService

__all__ = [
    "lambda_handler",
    "api_endpoint_handler",
    "FrameworkService",
]
