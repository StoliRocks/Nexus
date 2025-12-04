"""Science orchestrator business logic.

Handles ML pipeline orchestration: embed → retrieve → rerank.

Uses Nexus Database Schema key patterns:
- frameworkKey = "frameworkName#version" (e.g., "NIST-800-53#R5", "AWS.EC2#1.0")
- controlKey = "frameworkKey#controlId" (e.g., "NIST-800-53#R5#AC-1")
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Key

from nexus_science_orchestrator_lambda.science_client import (
    ScienceClient,
)

logger = logging.getLogger(__name__)

MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")

# Default versions for common frameworks (used when version not specified)
DEFAULT_FRAMEWORK_VERSIONS = {
    "NIST-800-53": "R5",
    "NIST-CSF": "2.0",
    "PCI-DSS": "4.0",
    "SOC2": "2017",
    "CIS": "8.0",
    "ISO-27001": "2022",
    "HIPAA": "2013",
    "HITRUST": "11.0",
}


class ScienceOrchestratorService:
    """Service class for ML pipeline orchestration operations."""

    def __init__(
        self,
        dynamodb_resource: Any = None,
        controls_table_name: Optional[str] = None,
        frameworks_table_name: Optional[str] = None,
        enrichment_table_name: Optional[str] = None,
        embedding_cache_table_name: Optional[str] = None,
        science_client: Optional[ScienceClient] = None,
    ):
        """
        Initialize the science orchestrator service.

        Args:
            dynamodb_resource: Optional DynamoDB resource (for testing).
            controls_table_name: Optional controls table name override.
            frameworks_table_name: Optional frameworks table name override.
            enrichment_table_name: Optional enrichment table name override.
            embedding_cache_table_name: Optional embedding cache table name override.
            science_client: Optional science client (for testing).
        """
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.controls_table_name = controls_table_name or os.environ.get(
            "CONTROLS_TABLE_NAME", "Controls"
        )
        self.frameworks_table_name = frameworks_table_name or os.environ.get(
            "FRAMEWORKS_TABLE_NAME", "Frameworks"
        )
        self.enrichment_table_name = enrichment_table_name or os.environ.get(
            "ENRICHMENT_TABLE_NAME", "Enrichment"
        )
        self.embedding_cache_table_name = embedding_cache_table_name or os.environ.get(
            "EMBEDDING_CACHE_TABLE_NAME", "EmbeddingCache"
        )

        self.controls_table = self.dynamodb.Table(self.controls_table_name)
        self.frameworks_table = self.dynamodb.Table(self.frameworks_table_name)
        self.enrichment_table = self.dynamodb.Table(self.enrichment_table_name)
        self.embedding_cache_table = self.dynamodb.Table(self.embedding_cache_table_name)

        self.science_client = science_client or ScienceClient()

    def validate_control(self, event: dict) -> dict:
        """
        Check if control exists in database.

        Args:
            event: Dict with control_key (full key) OR
                   control_id + framework_key (will be combined).

        Returns:
            Dict with exists (bool) and control (dict or None).
        """
        control_key = event.get("control_key")

        # If control_key not provided, try to build it from components
        if not control_key:
            control_id = event.get("control_id")
            framework_key = event.get("framework_key")
            if control_id and framework_key:
                control_key = self._build_control_key(framework_key, control_id)
            elif control_id:
                # Legacy: assume control_id IS the full control_key
                control_key = control_id

        if not control_key:
            return {"exists": False, "control": None, "error": "No control_key provided"}

        control = self._get_control(control_key)

        if control:
            return {"exists": True, "control": control, "control_key": control_key}
        return {"exists": False, "control": None, "control_key": control_key}

    def check_enrichment(self, event: dict) -> dict:
        """
        Check if enrichment exists for control.

        Args:
            event: Dict with control_key (preferred) or control_id.

        Returns:
            Dict with exists (bool) and enrichment (dict or None).
        """
        # Use control_key as the cache key
        control_key = event.get("control_key") or event.get("control_id")
        enrichment = self._get_enrichment(control_key)

        if enrichment:
            return {"exists": True, "enrichment": enrichment}
        return {"exists": False, "enrichment": None}

    def map_control(self, event: dict) -> dict:
        """
        Execute mapping pipeline: embed → retrieve → rerank.

        Args:
            event: Dict with:
                - control_key: Full source control key (e.g., "AWS.EC2#1.0#PR.1")
                  OR control_id (legacy, treated as full key)
                - target_framework_key: Target framework key (e.g., "NIST-800-53#R5")
                  OR target_framework + target_version (will be combined)
                - target_control_ids: Optional list of specific control IDs to filter.

        Returns:
            Dict with mappings list containing target_control_key, scores, text.
        """
        # Get source control key
        source_key = event.get("control_key") or event.get("control_id")
        if not source_key:
            return {"mappings": [], "error": "No source control specified"}

        # Get target framework key
        target_framework_key = event.get("target_framework_key")
        if not target_framework_key:
            target_framework = event.get("target_framework")
            target_version = event.get("target_version")
            if target_framework:
                target_framework_key = self._build_framework_key(target_framework, target_version)
            else:
                return {"mappings": [], "error": "No target framework specified"}

        target_control_ids = event.get("target_control_ids")

        # Get source control text
        control_text = self._get_control_text(source_key)
        source_embedding = self._get_or_create_embedding(source_key, control_text)

        # Get target controls
        targets = self._get_framework_controls(target_framework_key, target_control_ids)
        if not targets:
            return {"mappings": [], "target_framework_key": target_framework_key}

        target_embeddings, target_keys, target_texts = self._prepare_targets(targets)

        # Retrieve candidates
        candidates = self.science_client.call_retrieve(
            source_embedding, target_embeddings, target_keys, top_k=20
        )
        if not candidates:
            return {"mappings": [], "target_framework_key": target_framework_key}

        # Rerank candidates
        rerank_candidates = [
            {"control_key": c["control_id"], "text": target_texts[c["control_id"]]}
            for c in candidates
        ]
        rankings = self.science_client.call_rerank(control_text, rerank_candidates, threshold=0.5)

        return {
            "mappings": self._build_mappings(
                rankings, candidates, target_framework_key, target_texts
            ),
            "source_control_key": source_key,
            "target_framework_key": target_framework_key,
        }

    # =========================================================================
    # Key building utilities
    # =========================================================================

    def _parse_control_key(self, control_key: str) -> Tuple[str, str, str]:
        """
        Parse controlKey into components.

        Args:
            control_key: Full control key (frameworkName#version#controlId).

        Returns:
            Tuple of (frameworkName, version, controlId).
        """
        parts = control_key.split("#")
        if len(parts) >= 3:
            return parts[0], parts[1], "#".join(parts[2:])
        raise ValueError(f"Invalid controlKey format: {control_key}")

    def _build_framework_key(
        self, framework_name: str, version: Optional[str] = None
    ) -> str:
        """
        Build frameworkKey from components.

        Args:
            framework_name: Framework name (e.g., "NIST-800-53").
            version: Optional version (uses default if not specified).

        Returns:
            Framework key (e.g., "NIST-800-53#R5").
        """
        if version is None:
            version = DEFAULT_FRAMEWORK_VERSIONS.get(framework_name, "1.0")
        return f"{framework_name}#{version}"

    def _build_control_key(self, framework_key: str, control_id: str) -> str:
        """
        Build controlKey from frameworkKey and controlId.

        Args:
            framework_key: Framework key (frameworkName#version).
            control_id: Control identifier.

        Returns:
            Control key (e.g., "NIST-800-53#R5#AC-1").
        """
        return f"{framework_key}#{control_id}"

    # =========================================================================
    # Database operations
    # =========================================================================

    def _get_control(self, control_key: str) -> Optional[dict]:
        """
        Fetch control from database by controlKey.

        Args:
            control_key: Full control key (frameworkKey#controlId).

        Returns:
            Control record or None if not found.
        """
        # Query the ControlKeyIndex GSI
        result = self.controls_table.query(
            IndexName="ControlKeyIndex",
            KeyConditionExpression=Key("controlKey").eq(control_key),
            Limit=1,
        )
        items = result.get("Items", [])
        return self._convert_decimals(items[0]) if items else None

    def _get_enrichment(self, control_key: str) -> Optional[dict]:
        """
        Fetch control enrichment from cache.

        Args:
            control_key: Control key.

        Returns:
            Enrichment record or None if not found.
        """
        result = self.enrichment_table.get_item(Key={"control_id": control_key})
        item = result.get("Item")
        return self._convert_decimals(item) if item else None

    def _get_cached_embedding(
        self, control_key: str, model_version: str
    ) -> Optional[List[float]]:
        """
        Fetch cached embedding.

        Args:
            control_key: Control key.
            model_version: Model version string.

        Returns:
            Embedding vector or None if not cached.
        """
        result = self.embedding_cache_table.get_item(
            Key={"control_id": control_key, "model_version": model_version}
        )
        item = result.get("Item")
        if item and "embedding" in item:
            return [float(x) for x in item["embedding"]]
        return None

    def _cache_embedding(
        self, control_key: str, model_version: str, embedding: List[float]
    ) -> None:
        """
        Store embedding in cache.

        Args:
            control_key: Control key.
            model_version: Model version string.
            embedding: Embedding vector.
        """
        from decimal import Decimal

        # Convert floats to Decimal for DynamoDB
        embedding_decimal = [Decimal(str(x)) for x in embedding]
        self.embedding_cache_table.put_item(
            Item={
                "control_id": control_key,
                "model_version": model_version,
                "embedding": embedding_decimal,
            }
        )

    def _get_framework_controls(
        self, framework_key: str, control_ids: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Fetch all controls for a framework, optionally filtered by IDs.

        Args:
            framework_key: Framework key (frameworkName#version).
            control_ids: Optional list of specific control IDs to filter.

        Returns:
            List of control records.
        """
        if control_ids:
            # Fetch specific controls using batch get with primary key
            keys = [
                {"frameworkKey": framework_key, "controlKey": f"{framework_key}#{cid}"}
                for cid in control_ids
            ]
            controls = []
            # DynamoDB batch_get_item limit is 100 items
            for i in range(0, len(keys), 100):
                response = self.dynamodb.batch_get_item(
                    RequestItems={
                        self.controls_table_name: {"Keys": keys[i : i + 100]}
                    }
                )
                controls.extend(
                    response.get("Responses", {}).get(self.controls_table_name, [])
                )
            return [self._convert_decimals(c) for c in controls]

        # Query all controls for framework using partition key
        response = self.controls_table.query(
            KeyConditionExpression=Key("frameworkKey").eq(framework_key)
        )
        items = response.get("Items", [])

        # Handle pagination if there are more items
        while "LastEvaluatedKey" in response:
            response = self.controls_table.query(
                KeyConditionExpression=Key("frameworkKey").eq(framework_key),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        return [self._convert_decimals(item) for item in items]

    # =========================================================================
    # Pipeline helpers
    # =========================================================================

    def _get_control_text(self, control_key: str) -> str:
        """Get control text, preferring enriched version."""
        enrichment = self._get_enrichment(control_key)
        if enrichment and enrichment.get("enriched_text"):
            return enrichment["enriched_text"]

        control = self._get_control(control_key)
        if not control:
            raise ValueError(f"Control not found: {control_key}")

        # Try different field names for the text content
        return (
            control.get("description")
            or control.get("text")
            or control.get("title", "")
        )

    def _get_or_create_embedding(self, control_key: str, text: str) -> List[float]:
        """Get cached embedding or generate new one."""
        cached = self._get_cached_embedding(control_key, MODEL_VERSION)
        if cached:
            return cached

        embedding = self.science_client.call_embed(control_key, text)
        self._cache_embedding(control_key, MODEL_VERSION, embedding)
        return embedding

    def _prepare_targets(
        self, targets: List[dict]
    ) -> Tuple[List[List[float]], List[str], Dict[str, str]]:
        """
        Prepare target embeddings, keys, and text lookup.

        Args:
            targets: List of control records from database.

        Returns:
            Tuple of (embeddings, control_keys, texts_dict).
        """
        embeddings: List[List[float]] = []
        keys: List[str] = []
        texts: Dict[str, str] = {}

        for target in targets:
            control_key = target["controlKey"]
            keys.append(control_key)

            # Get text from various possible fields
            text = (
                target.get("description")
                or target.get("text")
                or target.get("title", "")
            )
            texts[control_key] = text

            emb = self._get_or_create_embedding(control_key, text)
            embeddings.append(emb)

        return embeddings, keys, texts

    def _build_mappings(
        self,
        rankings: List[dict],
        candidates: List[dict],
        target_framework_key: str,
        texts: Dict[str, str],
    ) -> List[dict]:
        """Build final mapping results with scores."""
        similarity_map = {c["control_id"]: c["similarity_score"] for c in candidates}

        mappings = []
        for r in rankings:
            control_key = r.get("control_key") or r.get("control_id")
            # Extract controlId from controlKey
            parts = control_key.split("#")
            control_id = parts[-1] if parts else control_key

            mappings.append(
                {
                    "target_control_key": control_key,
                    "target_control_id": control_id,
                    "target_framework_key": target_framework_key,
                    "similarity_score": similarity_map.get(control_key, 0.0),
                    "rerank_score": r.get("rerank_score", 0.0),
                    "text": texts.get(control_key, ""),
                }
            )

        return mappings

    def _convert_decimals(self, obj: Any) -> Any:
        """Convert DynamoDB Decimal types to float."""
        from decimal import Decimal

        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert_decimals(i) for i in obj]
        return obj
