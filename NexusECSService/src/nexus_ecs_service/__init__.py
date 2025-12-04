"""
Nexus ECS Service - GPU ML Inference for Control Mapping.

This package provides FastAPI endpoints for:
- Embedding generation using Qwen bi-encoder
- Cosine similarity retrieval
- Cross-encoder reranking using ModernBERT
"""

from nexus_ecs_service.interfaces import BaseRetriever, BaseReranker
from nexus_ecs_service.algorithms.retrievers import QwenRetriever
from nexus_ecs_service.algorithms.rerankers import ModernBERTReranker

__version__ = "1.0.0"
__all__ = [
    "BaseRetriever",
    "BaseReranker",
    "QwenRetriever",
    "ModernBERTReranker",
]
