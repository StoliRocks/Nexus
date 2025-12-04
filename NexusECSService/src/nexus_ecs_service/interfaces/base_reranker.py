"""
Base interface for reranking models.

Defines the contract that all reranker implementations must follow.
This interface ensures consistent behavior across different reranker types.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np


class BaseReranker(ABC):
    """
    Abstract base class for reranking models.

    All reranker implementations must inherit from this class and implement
    the required methods. This ensures a consistent interface across different
    reranking models (ModernBERT, Qwen, CrossEncoder, etc.).
    """

    @abstractmethod
    def predict(
        self,
        pairs: List[Tuple[str, str]],
        batch_size: int = 16,
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """
        Score query-document pairs.

        **SIGNATURE MUST NOT CHANGE** - This is the contract.

        Args:
            pairs: List of (query, document) text tuples
            batch_size: Batch size for processing
            show_progress_bar: Whether to show progress bar

        Returns:
            Array of scores for each pair (typically in [0, 1] range)
        """
        pass
