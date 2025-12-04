"""FastAPI science endpoint client for ECS inference service."""

import json
import os
import random
from typing import List, Optional

import urllib3

SCIENCE_API_ENDPOINT = os.environ.get("SCIENCE_API_ENDPOINT", "")
SCIENCE_TIMEOUT_SECONDS = 60.0  # Longer timeout for ML inference

# Use mock only if explicitly enabled OR no endpoint configured
USE_MOCK = (
    os.environ.get("USE_MOCK_SCIENCE", "false").lower() == "true"
    or not SCIENCE_API_ENDPOINT
)


class ScienceClient:
    """Client for ECS ML inference service."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        use_mock: Optional[bool] = None,
        timeout: float = SCIENCE_TIMEOUT_SECONDS,
    ):
        """
        Initialize the science client.

        Args:
            endpoint: Optional endpoint URL override.
            use_mock: Optional mock mode override.
            timeout: Request timeout in seconds.
        """
        self.endpoint = endpoint or SCIENCE_API_ENDPOINT
        self.use_mock = use_mock if use_mock is not None else USE_MOCK
        self.timeout = timeout
        self.http = urllib3.PoolManager()

    def call_embed(self, control_id: str, text: str) -> List[float]:
        """
        Generate embedding via FastAPI /embed endpoint.

        Args:
            control_id: Control identifier.
            text: Control text to embed.

        Returns:
            4096-dimensional embedding vector.

        Raises:
            RuntimeError: API returns non-200 status.
        """
        if self.use_mock:
            return self._mock_embed(control_id, text)
        return self._call_api(
            "/api/v1/embed", {"control_id": control_id, "text": text}
        ).get("embedding", [])

    def call_retrieve(
        self,
        source_embedding: List[float],
        target_embeddings: List[List[float]],
        target_control_ids: List[str],
        top_k: int = 20,
    ) -> List[dict]:
        """
        Retrieve top-k similar controls via FastAPI /retrieve endpoint.

        Args:
            source_embedding: Source control embedding.
            target_embeddings: List of target control embeddings.
            target_control_ids: List of target control IDs.
            top_k: Number of top candidates to return.

        Returns:
            List of dicts with control_id and similarity_score.

        Raises:
            RuntimeError: API returns non-200 status.
        """
        if self.use_mock:
            return self._mock_retrieve(target_control_ids, top_k)
        return self._call_api(
            "/api/v1/retrieve",
            {
                "source_embedding": source_embedding,
                "target_embeddings": target_embeddings,
                "target_control_ids": target_control_ids,
                "top_k": top_k,
            },
        ).get("candidates", [])

    def call_rerank(
        self, source_text: str, candidates: List[dict], threshold: float = 0.5
    ) -> List[dict]:
        """
        Rerank candidates via FastAPI /rerank endpoint.

        Args:
            source_text: Source control text.
            candidates: List of candidate dicts with control_key and text.
            threshold: Minimum rerank score threshold.

        Returns:
            List of dicts with control_id and rerank_score above threshold.

        Raises:
            RuntimeError: API returns non-200 status.
        """
        if self.use_mock:
            return self._mock_rerank(candidates, threshold)
        return self._call_api(
            "/api/v1/rerank",
            {
                "source_text": source_text,
                "candidates": candidates,
                "threshold": threshold,
            },
        ).get("rankings", [])

    # =========================================================================
    # Mock implementations for testing orchestration pipeline
    # =========================================================================

    def _mock_embed(self, control_id: str, text: str) -> List[float]:
        """Generate deterministic mock embedding based on text hash."""
        seed = hash(text) % 10000
        random.seed(seed)
        embedding = [random.uniform(-1, 1) for _ in range(4096)]
        norm = sum(x * x for x in embedding) ** 0.5
        return [x / norm for x in embedding]

    def _mock_retrieve(
        self, target_control_ids: List[str], top_k: int
    ) -> List[dict]:
        """Return mock similarity scores for target controls."""
        candidates = []
        for i, control_id in enumerate(target_control_ids[:top_k]):
            score = max(0.3, 1.0 - (i * 0.05) + random.uniform(-0.1, 0.1))
            candidates.append(
                {"control_id": control_id, "similarity_score": round(score, 3)}
            )
        return sorted(candidates, key=lambda x: x["similarity_score"], reverse=True)

    def _mock_rerank(
        self, candidates: List[dict], threshold: float
    ) -> List[dict]:
        """Return mock rerank scores, filtering by threshold."""
        rankings = []
        for i, c in enumerate(candidates):
            score = max(0.2, 0.95 - (i * 0.08) + random.uniform(-0.05, 0.05))
            if score >= threshold:
                rankings.append(
                    {
                        "control_id": c.get("control_key") or c.get("control_id"),
                        "rerank_score": round(score, 3),
                    }
                )
        return rankings

    # =========================================================================
    # Real API client
    # =========================================================================

    def _call_api(self, endpoint: str, payload: dict) -> dict:
        """
        Call FastAPI science endpoint.

        Args:
            endpoint: API endpoint path.
            payload: Request payload.

        Returns:
            Response JSON as dict.

        Raises:
            RuntimeError: API returns non-200 status.
        """
        if self.use_mock:
            raise RuntimeError("Mock mode enabled - real API calls disabled")

        url = f"{self.endpoint}{endpoint}"
        response = self.http.request(
            "POST",
            url,
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if response.status != 200:
            raise RuntimeError(
                f"Science API error: {response.status} - {response.data.decode('utf-8')}"
            )
        return json.loads(response.data.decode("utf-8"))
