"""ModernBERT-based reranker for document ranking."""

from typing import List, Tuple

import numpy as np
import torch
from sentence_transformers import CrossEncoder

from nexus_ecs_service.interfaces.base_reranker import BaseReranker


class ModernBERTReranker(BaseReranker):
    """Wrapper for Alibaba-NLP/gte-reranker-modernbert-base reranker."""

    def __init__(
        self,
        model_name: str = "Alibaba-NLP/gte-reranker-modernbert-base",
        device: str = "cuda"
    ):
        """
        Initialize ModernBERT reranker.

        Args:
            model_name: Model name (default: Alibaba-NLP/gte-reranker-modernbert-base)
            device: Device to use (cuda, cpu)
        """
        # Initialize CrossEncoder with bfloat16 for Flash Attention 2 support
        self.model = CrossEncoder(
            model_name,
            model_kwargs={"torch_dtype": torch.bfloat16},
            device=device
        )

        self.model_name = model_name
        self.device = device

    def predict(
        self,
        pairs: List[Tuple[str, str]],
        batch_size: int = 16,
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """
        Score query-document pairs (compatible with CrossEncoder interface).

        Args:
            pairs: List of (query, document) tuples
            batch_size: Batch size for processing
            show_progress_bar: Whether to show progress bar

        Returns:
            Array of scores (probabilities in [0, 1] range due to softmax)
        """
        scores = self.model.predict(
            pairs,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar
        )

        if not isinstance(scores, np.ndarray):
            scores = np.array(scores)

        return scores
