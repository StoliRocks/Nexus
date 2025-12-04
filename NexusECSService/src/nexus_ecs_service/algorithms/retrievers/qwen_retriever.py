"""Qwen-based retriever with caching support for embedding generation."""

import hashlib
import pickle
from pathlib import Path
from typing import List, Tuple

import torch
import torch.nn.functional as F
from torch import Tensor
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

from nexus_ecs_service.interfaces.base_retriever import BaseRetriever


def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    """
    Pool embeddings using last token (for Qwen models with left padding).

    Args:
        last_hidden_states: Hidden states from model
        attention_mask: Attention mask

    Returns:
        Pooled embeddings
    """
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[
            torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths
        ]


def get_detailed_instruct(task_description: str, query: str) -> str:
    """
    Format query with task instruction (for retrieval models).

    Args:
        task_description: Task description
        query: Query text

    Returns:
        Formatted query with instruction
    """
    return f'Instruct: {task_description}\nQuery: {query}'


def check_embeddings_cached(
    texts: List[str],
    with_instruction: bool,
    model_name: str,
    max_length: int,
    cache_dir: str
) -> bool:
    """
    Check if embeddings are already cached without loading model.

    Args:
        texts: List of texts
        with_instruction: Whether instruction will be added
        model_name: Model name
        max_length: Max sequence length
        cache_dir: Cache directory

    Returns:
        True if cache exists, False otherwise
    """
    text_content = "||".join(texts)
    text_hash = hashlib.md5(text_content.encode()).hexdigest()[:16]
    model_short = model_name.split('/')[-1]
    instruction_str = "with_inst" if with_instruction else "no_inst"
    cache_key = f"{model_short}_{instruction_str}_{max_length}_{len(texts)}_{text_hash}.pkl"

    cache_file = Path(cache_dir) / cache_key
    return cache_file.exists()


def load_embeddings_from_cache(
    texts: List[str],
    with_instruction: bool,
    model_name: str,
    max_length: int,
    cache_dir: str
) -> torch.Tensor:
    """
    Load embeddings directly from cache without loading model.

    Args:
        texts: List of texts
        with_instruction: Whether instruction was added
        model_name: Model name
        max_length: Max sequence length
        cache_dir: Cache directory

    Returns:
        Cached embeddings tensor
    """
    text_content = "||".join(texts)
    text_hash = hashlib.md5(text_content.encode()).hexdigest()[:16]
    model_short = model_name.split('/')[-1]
    instruction_str = "with_inst" if with_instruction else "no_inst"
    cache_key = f"{model_short}_{instruction_str}_{max_length}_{len(texts)}_{text_hash}.pkl"

    cache_file = Path(cache_dir) / cache_key

    with open(cache_file, 'rb') as f:
        return pickle.load(f)


class QwenRetriever(BaseRetriever):
    """Retriever using Qwen3-Embedding model with caching support."""

    def __init__(
        self,
        model_name: str,
        device: str = "cuda",
        max_length: int = 8192,
        cache_dir: str = "cache/embeddings",
        use_cache: bool = True,
        with_instruction: bool = False
    ):
        """
        Initialize Qwen retriever.

        Args:
            model_name: Model name (e.g., Qwen/Qwen3-Embedding-8B)
            device: Device to use
            max_length: Maximum sequence length
            cache_dir: Directory to cache embeddings
            use_cache: Whether to use caching
            with_instruction: Whether to prepend task instruction (query vs document mode)
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, padding_side='left')
        # Multi-GPU FP32 loading: spread model across all available GPUs
        self.model = AutoModel.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        self.model.eval()
        self.device = "cuda"
        self.max_length = max_length
        self.model_name = model_name

        # Task instruction for AWS-to-framework mapping
        self._task_instruction = (
            'Given an AWS security control, retrieve industry framework controls '
            'that address the same security objective'
        )

        # Internal config: whether to use instruction (query vs document mode)
        self.with_instruction = with_instruction

        # Cache setup
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.use_cache and self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def task_instruction(self) -> str:
        """Get the task instruction for query formatting."""
        return self._task_instruction

    def _get_cache_key(self, texts: List[str], with_instruction: bool) -> str:
        """
        Generate unique cache key from texts and settings.

        Args:
            texts: List of texts
            with_instruction: Whether instruction was added

        Returns:
            Cache filename
        """
        text_content = "||".join(texts)
        text_hash = hashlib.md5(text_content.encode()).hexdigest()[:16]
        model_short = self.model_name.split('/')[-1]
        instruction_str = "with_inst" if with_instruction else "no_inst"
        return f"{model_short}_{instruction_str}_{self.max_length}_{len(texts)}_{text_hash}.pkl"

    def _load_from_cache(self, cache_key: str) -> torch.Tensor:
        """Load embeddings from cache."""
        cache_file = self.cache_dir / cache_key
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def _save_to_cache(self, embeddings: torch.Tensor, cache_key: str):
        """Save embeddings to cache."""
        cache_file = self.cache_dir / cache_key
        with open(cache_file, 'wb') as f:
            pickle.dump(embeddings, f)

    def encode(
        self,
        texts: List[str],
        batch_size: int = 8,
        show_progress: bool = True
    ) -> torch.Tensor:
        """
        Encode texts to embeddings with optional caching.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar

        Returns:
            Normalized embeddings tensor
        """
        # Try loading from cache
        if self.use_cache and self.cache_dir:
            cache_key = self._get_cache_key(texts, self.with_instruction)
            cached_embeddings = self._load_from_cache(cache_key)

            if cached_embeddings is not None:
                return cached_embeddings

        # Cache miss or caching disabled - encode
        processed_texts = texts
        if self.with_instruction:
            processed_texts = [
                get_detailed_instruct(self.task_instruction, text) for text in texts
            ]

        all_embeddings = []

        iterator = range(0, len(texts), batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Encoding")

        with torch.no_grad():
            for i in iterator:
                batch_texts = processed_texts[i:i + batch_size]

                batch_dict = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )
                batch_dict = {k: v.to(self.device) for k, v in batch_dict.items()}

                outputs = self.model(**batch_dict)
                embeddings = last_token_pool(
                    outputs.last_hidden_state,
                    batch_dict['attention_mask']
                )

                embeddings = F.normalize(embeddings, p=2, dim=1)
                all_embeddings.append(embeddings.cpu())

        embeddings = torch.cat(all_embeddings, dim=0)

        # Save to cache
        if self.use_cache and self.cache_dir:
            self._save_to_cache(embeddings, cache_key)

        return embeddings

    def retrieve(
        self,
        aws_embeddings: torch.Tensor,
        fc_embeddings: torch.Tensor,
        fc_ids: List[Tuple[str, str]],
        top_k: int = 50
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Retrieve top-K framework controls per framework for each AWS control.

        Args:
            aws_embeddings: AWS control embeddings
            fc_embeddings: Framework control embeddings
            fc_ids: List of (framework, control_id) tuples
            top_k: Number of candidates to retrieve PER FRAMEWORK

        Returns:
            Tuple of (top_k_indices, top_k_scores)
        """
        similarities = torch.mm(aws_embeddings, fc_embeddings.T)

        # Group by framework
        framework_groups = {}
        for idx, (framework, _) in enumerate(fc_ids):
            if framework not in framework_groups:
                framework_groups[framework] = []
            framework_groups[framework].append(idx)

        # Get top-K per framework
        all_indices = []
        all_scores = []

        for i in range(len(aws_embeddings)):
            aws_indices = []
            aws_scores = []

            for framework, framework_indices in framework_groups.items():
                framework_indices_tensor = torch.tensor(framework_indices, dtype=torch.long)
                framework_sims = similarities[i, framework_indices_tensor]

                k = min(top_k, len(framework_indices))
                topk_scores, topk_local_indices = torch.topk(framework_sims, k=k)
                topk_global_indices = framework_indices_tensor[topk_local_indices]

                aws_indices.append(topk_global_indices)
                aws_scores.append(topk_scores)

            all_indices.append(torch.cat(aws_indices))
            all_scores.append(torch.cat(aws_scores))

        # Stack into tensors
        max_len = max(len(idx) for idx in all_indices)

        # Pad to same length
        padded_indices = []
        padded_scores = []
        for indices, scores in zip(all_indices, all_scores):
            if len(indices) < max_len:
                pad_size = max_len - len(indices)
                indices = torch.cat([indices, torch.zeros(pad_size, dtype=torch.long)])
                scores = torch.cat([scores, torch.zeros(pad_size)])
            padded_indices.append(indices)
            padded_scores.append(scores)

        top_k_indices = torch.stack(padded_indices)
        top_k_scores = torch.stack(padded_scores)

        return top_k_indices, top_k_scores
