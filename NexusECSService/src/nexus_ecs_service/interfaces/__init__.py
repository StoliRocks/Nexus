"""Base interfaces for ML models."""

from nexus_ecs_service.interfaces.base_retriever import BaseRetriever
from nexus_ecs_service.interfaces.base_reranker import BaseReranker

__all__ = ["BaseRetriever", "BaseReranker"]
