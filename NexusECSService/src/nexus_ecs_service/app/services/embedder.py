"""
Embedding generation service using retriever implementations.

Wraps BaseRetriever implementations for use in the ECS service.
"""

import torch
import numpy as np
from typing import Dict, List
import time

from nexus_ecs_service.interfaces.base_retriever import BaseRetriever
from nexus_ecs_service.app.services.embedding_cache import EmbeddingCacheService
from nexus_ecs_service.app.config import settings
from nexus_ecs_service.app.aws_logger import StructuredLogger

logger = StructuredLogger("nexus-ecs-service")


class EmbedderService:
    """
    Service for generating control embeddings using retrievers.

    Uses BaseRetriever interface. The with_instruction setting
    is an internal model configuration set at initialization time.
    """

    def __init__(self, model: BaseRetriever, embedding_cache: EmbeddingCacheService):
        """
        Initialize embedder service.

        Args:
            model: BaseRetriever instance (configured at init for query/document mode)
            embedding_cache: EmbeddingCacheService instance
        """
        self.model = model
        self.cache = embedding_cache
        self.model_version = "qwen-8b-v1"

    async def get_or_generate_embedding(
        self,
        control_id: str,
        text: str
    ) -> Dict:
        """
        Get embedding from cache or generate new one.

        Args:
            control_id: Control ID for caching
            text: Control text to embed

        Returns:
            Dictionary with embedding (as list), cache_hit flag
        """
        start_time = time.time()

        # Check cache first
        cached_emb = await self.cache.get_embedding(control_id, self.model_version)

        if cached_emb is not None:
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Embedding retrieved from cache",
                control_id=control_id,
                execution_time_ms=execution_time_ms,
                cache_hit=True
            )

            return {
                'embedding': cached_emb.tolist(),
                'cache_hit': True
            }

        # Generate new embedding
        logger.info(
            "Generating new embedding",
            control_id=control_id,
            text_length=len(text)
        )

        try:
            embedding = self.model.encode(
                [text],
                batch_size=1,
                show_progress=False
            )[0]

            embedding_np = embedding.cpu().numpy() if isinstance(embedding, torch.Tensor) else embedding

            await self.cache.put_embedding(
                control_id,
                self.model_version,
                embedding_np
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Embedding generated and cached",
                control_id=control_id,
                embedding_dim=len(embedding_np),
                execution_time_ms=execution_time_ms,
                cache_hit=False
            )

            return {
                'embedding': embedding_np.tolist(),
                'cache_hit': False
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "Error generating embedding",
                control_id=control_id,
                error_type=type(e).__name__,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
            raise

    async def batch_embed(
        self,
        texts: List[str],
        control_ids: List[str] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of control texts
            control_ids: Optional list of control IDs for caching

        Returns:
            List of embeddings as lists of floats
        """
        start_time = time.time()

        logger.info(
            "Batch embedding generation started",
            batch_size=len(texts)
        )

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=settings.max_batch_size,
                show_progress=False
            )

            embeddings_np = embeddings.cpu().numpy() if isinstance(embeddings, torch.Tensor) else embeddings
            embeddings_list = embeddings_np.tolist()

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Batch embedding generation complete",
                batch_size=len(texts),
                execution_time_ms=execution_time_ms,
                avg_time_per_item_ms=execution_time_ms // len(texts) if texts else 0
            )

            return embeddings_list

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "Error in batch embedding generation",
                batch_size=len(texts),
                error_type=type(e).__name__,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
            raise
