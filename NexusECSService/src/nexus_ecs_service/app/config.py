"""
Configuration management for Nexus ECS Service.

Uses Pydantic Settings for environment variable validation and type safety.
"""

from pydantic_settings import BaseSettings
import torch


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Configuration
    aws_region: str = "us-east-1"
    s3_bucket: str = "nexus-science"
    s3_models_prefix: str = "models"

    # Model Configuration
    model_dir: str = "/tmp/models"
    qwen_model_path: str = "qwen-embedding-8b"
    reranker_model_path: str = "modernbert-reranker"

    # DynamoDB Tables
    embedding_cache_table: str = "nexus-embedding-cache"
    framework_controls_table: str = "FrameworkControls"

    # Model Settings
    max_batch_size: int = 32
    max_sequence_length: int = 8192
    embedding_dimension: int = 4096

    # Compute device
    @property
    def device(self) -> str:
        """Determine compute device (cuda if available, else cpu)."""
        return "cuda" if torch.cuda.is_available() else "cpu"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""


# Global settings instance
settings = Settings()
