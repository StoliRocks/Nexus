"""
Base interface for retrieval models.

Defines the contract that all retriever implementations must follow.
This interface ensures consistent behavior across different retriever types.
"""

from abc import ABC, abstractmethod
from typing import List
import torch


class BaseRetriever(ABC):
    """
    Abstract base class for retrieval models.

    All retriever implementations must inherit from this class and implement
    the required methods. This ensures a consistent interface across different
    retrieval models (Qwen, BERT, etc.).
    """

    @property
    @abstractmethod
    def task_instruction(self) -> str:
        """
        Get the task instruction for query formatting.

        This instruction describes the retrieval task and is prepended
        to queries when with_instruction=True in encode().

        Returns:
            Task instruction string
        """
        pass

    @abstractmethod
    def encode(
        self,
        texts: List[str],
        batch_size: int = 8,
        show_progress: bool = True
    ) -> torch.Tensor:
        """
        Encode texts to embeddings.

        **SIGNATURE MUST NOT CHANGE** - This is the contract.

        Whether to use task instructions is an internal model configuration,
        set at initialization time based on the use case (query vs document encoding).

        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar

        Returns:
            Normalized embeddings tensor of shape (len(texts), embedding_dim)
        """
        pass
