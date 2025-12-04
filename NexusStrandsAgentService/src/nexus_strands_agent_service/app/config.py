"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service identification
    service_name: str = "nexus-strands-agent-service"
    environment: str = "development"

    # AWS configuration
    aws_region: str = "us-east-1"

    # Bedrock configuration for agents
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    reasoning_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"

    # Cross-account Bedrock access (if needed)
    bedrock_role_arn: Optional[str] = None
    bedrock_external_id: Optional[str] = None

    # Logging
    log_level: str = "INFO"

    # Request configuration
    request_timeout_seconds: int = 300  # 5 minutes for agent processing
    max_concurrent_agents: int = 5

    class Config:
        env_prefix = ""
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
