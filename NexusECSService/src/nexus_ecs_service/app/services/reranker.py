"""
Cross-encoder reranking service using reranker implementations.

Wraps BaseReranker implementations for use in the ECS service.
"""

from typing import List, Dict
import time

from nexus_ecs_service.interfaces.base_reranker import BaseReranker
from nexus_ecs_service.app.aws_logger import StructuredLogger

logger = StructuredLogger("nexus-ecs-service")


class RerankerService:
    """
    Service for reranking control candidates using rerankers.

    Uses BaseReranker interface to ensure consistency
    across different reranking models (ModernBERT, Qwen, etc.).
    """

    def __init__(self, model: BaseReranker):
        """
        Initialize reranker service.

        Args:
            model: BaseReranker instance
        """
        self.model = model

        logger.info(
            "Initialized reranker service",
            model_type=type(model).__name__
        )

    async def rerank_candidates(
        self,
        source_text: str,
        candidates: List[Dict],
        threshold: float = 0.8
    ) -> List[Dict]:
        """
        Rerank candidates using cross-encoder.

        Args:
            source_text: Source control text
            candidates: List of candidate dicts with 'text' field
            threshold: Minimum score to include in results

        Returns:
            List of ranked candidates above threshold, sorted by score
        """
        start_time = time.time()

        logger.info(
            "Reranking started",
            num_candidates=len(candidates),
            threshold=threshold
        )

        if not candidates:
            logger.warning("No candidates to rerank")
            return []

        try:
            # Create (source, candidate) pairs
            pairs = [
                (source_text, candidate['text'])
                for candidate in candidates
            ]

            # Use reranker's predict method (BaseReranker interface)
            scores = self.model.predict(
                pairs,
                batch_size=32,
                show_progress_bar=False
            )

            # Filter by threshold and create rankings
            rankings = []
            for candidate, score in zip(candidates, scores):
                if float(score) >= threshold:
                    rankings.append({
                        'framework': candidate.get('framework', ''),
                        'control_id': candidate['control_id'],
                        'score': float(score)
                    })

            # Sort by score descending
            rankings.sort(key=lambda x: x['score'], reverse=True)

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Reranking complete",
                num_candidates=len(candidates),
                num_above_threshold=len(rankings),
                threshold=threshold,
                execution_time_ms=execution_time_ms,
                avg_time_per_pair_ms=execution_time_ms // len(candidates) if candidates else 0
            )

            return rankings

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "Error in reranking",
                num_candidates=len(candidates),
                error_type=type(e).__name__,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
            raise
