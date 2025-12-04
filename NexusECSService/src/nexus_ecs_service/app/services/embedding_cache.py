"""
DynamoDB embedding cache service.

Provides caching layer for control embeddings to avoid regenerating
expensive ML embeddings on every request.
"""

import boto3
import numpy as np
import base64
from typing import Optional, Dict, List
from botocore.exceptions import ClientError
from datetime import datetime

from nexus_ecs_service.app.config import settings
from nexus_ecs_service.app.aws_logger import StructuredLogger

logger = StructuredLogger("nexus-ecs-service")


class EmbeddingCacheService:
    """
    Service for caching embeddings in DynamoDB.

    Embeddings are stored as base64-encoded numpy arrays for efficient storage
    and retrieval. Cache keys are control_key + model_version.
    """

    def __init__(self):
        """Initialize DynamoDB connection."""
        dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.table = dynamodb.Table(settings.embedding_cache_table)

        logger.info(
            "Initialized embedding cache",
            table=settings.embedding_cache_table,
            region=settings.aws_region
        )

    async def get_embedding(
        self,
        control_key: str,
        model_version: str
    ) -> Optional[np.ndarray]:
        """
        Get embedding from cache.

        Args:
            control_key: Control key (e.g., 'AWS.ControlCatalog#1.0#IAM.21')
            model_version: Model version (e.g., 'qwen-8b-v1')

        Returns:
            Numpy array if cached, None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'control_key': control_key,
                    'model_version': model_version
                }
            )

            if 'Item' in response:
                embedding_b64 = response['Item']['embedding']
                embedding_bytes = base64.b64decode(embedding_b64)
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)

                logger.debug(
                    "Cache hit",
                    control_key=control_key,
                    model_version=model_version,
                    embedding_dim=len(embedding)
                )

                return embedding

            logger.debug(
                "Cache miss",
                control_key=control_key,
                model_version=model_version
            )
            return None

        except ClientError as e:
            logger.error(
                "Error getting embedding from cache",
                control_key=control_key,
                error_code=e.response['Error']['Code'],
                error_message=e.response['Error']['Message']
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error getting embedding from cache",
                control_key=control_key,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return None

    async def put_embedding(
        self,
        control_key: str,
        model_version: str,
        embedding: np.ndarray
    ) -> bool:
        """
        Store embedding in cache.

        Args:
            control_key: Control key
            model_version: Model version
            embedding: Numpy array embedding

        Returns:
            True if successful, False otherwise
        """
        try:
            embedding_bytes = embedding.astype(np.float32).tobytes()
            embedding_b64 = base64.b64encode(embedding_bytes).decode('utf-8')

            self.table.put_item(
                Item={
                    'control_key': control_key,
                    'model_version': model_version,
                    'embedding': embedding_b64,
                    'embedding_dimension': len(embedding),
                    'created_at': datetime.utcnow().isoformat() + 'Z',
                    'model_name': 'qwen-embedding-8b'
                }
            )

            logger.debug(
                "Cached embedding",
                control_key=control_key,
                model_version=model_version,
                embedding_dim=len(embedding)
            )

            return True

        except ClientError as e:
            logger.error(
                "Error putting embedding to cache",
                control_key=control_key,
                error_code=e.response['Error']['Code'],
                error_message=e.response['Error']['Message']
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error putting embedding to cache",
                control_key=control_key,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return False

    async def batch_get_embeddings(
        self,
        control_keys: List[str],
        model_version: str
    ) -> Dict[str, Optional[np.ndarray]]:
        """
        Get multiple embeddings from cache in a single batch operation.

        Args:
            control_keys: List of control keys
            model_version: Model version

        Returns:
            Dictionary mapping control_key -> embedding (or None if not cached)
        """
        results = {}

        # DynamoDB batch_get_item has a limit of 100 items
        for i in range(0, len(control_keys), 100):
            batch_keys = control_keys[i:i + 100]

            try:
                response = boto3.resource('dynamodb').batch_get_item(
                    RequestItems={
                        settings.embedding_cache_table: {
                            'Keys': [
                                {
                                    'control_key': key,
                                    'model_version': model_version
                                }
                                for key in batch_keys
                            ]
                        }
                    }
                )

                if settings.embedding_cache_table in response.get('Responses', {}):
                    for item in response['Responses'][settings.embedding_cache_table]:
                        control_key = item['control_key']
                        embedding_b64 = item['embedding']
                        embedding_bytes = base64.b64decode(embedding_b64)
                        embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                        results[control_key] = embedding

                # Mark uncached keys as None
                for key in batch_keys:
                    if key not in results:
                        results[key] = None

            except Exception as e:
                logger.error(
                    "Error in batch get embeddings",
                    batch_size=len(batch_keys),
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                for key in batch_keys:
                    results[key] = None

        cache_hits = sum(1 for v in results.values() if v is not None)
        logger.info(
            "Batch embedding lookup complete",
            total_keys=len(control_keys),
            cache_hits=cache_hits,
            cache_hit_rate=round(cache_hits / len(control_keys) * 100, 2) if control_keys else 0
        )

        return results
