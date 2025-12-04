"""Configuration utilities for NexusEnrichmentAgent."""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def load_session_params(bedrock_only: bool = False) -> Optional[Dict]:
    """
    Load AWS session parameters from environment variables.

    Args:
        bedrock_only: If True, only load parameters needed for Bedrock access.
                     If False, load full session params including role assumption.

    Returns:
        Dictionary of session parameters or None if not configured.

    Environment Variables:
        AWS_REGION: AWS region (default: us-east-1)
        AWS_PROFILE: AWS profile name (optional)
        AWS_ROLE_ARN: Role ARN to assume (optional, for full access)
        BEDROCK_REGION: Region for Bedrock API (optional, overrides AWS_REGION)
    """
    params = {}

    # Get region
    region = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION", "us-east-1")
    params["region_name"] = region

    # Get profile if specified
    profile = os.environ.get("AWS_PROFILE")
    if profile:
        params["profile_name"] = profile

    # For full access (not bedrock_only), check for role assumption
    if not bedrock_only:
        role_arn = os.environ.get("AWS_ROLE_ARN")
        if role_arn:
            # Return params that can be used with STS assume_role
            params["role_arn"] = role_arn
            logger.debug(f"Configured for role assumption: {role_arn}")

    if len(params) <= 1:  # Only region_name
        return None

    return params


def get_model_id(default: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0") -> str:
    """
    Get the Bedrock model ID from environment or use default.

    Args:
        default: Default model ID to use if not configured.

    Returns:
        Model ID string.

    Environment Variables:
        BEDROCK_MODEL_ID: Model ID to use
    """
    return os.environ.get("BEDROCK_MODEL_ID", default)


def get_s3_bucket() -> Optional[str]:
    """
    Get the S3 bucket for framework data.

    Returns:
        S3 bucket name or None if not configured.

    Environment Variables:
        NEXUS_S3_BUCKET: S3 bucket name
    """
    return os.environ.get("NEXUS_S3_BUCKET")
