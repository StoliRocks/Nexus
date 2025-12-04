"""
Model loading and initialization from S3.

Downloads ML models from S3 on container startup and initializes them using
retriever and reranker classes.
"""

import os
import sys
import asyncio
import concurrent.futures
import logging
import boto3
from pathlib import Path
from typing import Dict

from nexus_ecs_service.algorithms.retrievers import QwenRetriever
from nexus_ecs_service.algorithms.rerankers import ModernBERTReranker
from nexus_ecs_service.app.config import settings
from nexus_ecs_service.app.aws_logger import StructuredLogger

logger = StructuredLogger("nexus-ecs-service")

# Standard logging for thread-safe progress updates
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
progress_logger = logging.getLogger("s3_download")
progress_logger.setLevel(logging.INFO)

# Global model storage - shared across all requests
MODELS: Dict = {}

# Thread pool for blocking operations
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


async def load_models_from_s3():
    """
    Download and initialize models from S3.

    Models are downloaded to local storage (/tmp/models) if not already present,
    then loaded using retriever and reranker classes.
    """
    try:
        s3_client = boto3.client("s3", region_name=settings.aws_region)

        os.makedirs(settings.model_dir, exist_ok=True)

        logger.info(
            "Starting model loading",
            model_dir=settings.model_dir,
            device=settings.device
        )

        # Load Qwen retriever
        await _load_qwen_retriever(s3_client)

        # Load ModernBERT reranker
        await _load_reranker(s3_client)

        logger.info(
            "All models loaded successfully",
            models_loaded=list(MODELS.keys()),
            device=settings.device
        )

    except Exception as e:
        logger.error(
            "Failed to load models from S3",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise


async def _load_qwen_retriever(s3_client):
    """Load Qwen retriever."""
    qwen_path = Path(settings.model_dir) / settings.qwen_model_path

    if not qwen_path.exists():
        logger.info("Downloading Qwen embedding model from S3")
        await download_model_from_s3(
            s3_client,
            f"{settings.s3_models_prefix}/{settings.qwen_model_path}/",
            qwen_path
        )
    else:
        logger.info("Qwen model found locally, skipping download")

    logger.info("Loading Qwen retriever")

    loop = asyncio.get_event_loop()
    retriever = await loop.run_in_executor(
        _executor,
        _create_qwen_retriever,
        str(qwen_path)
    )
    MODELS["retriever"] = retriever

    logger.info(
        "Qwen retriever loaded successfully",
        model_type="QwenRetriever",
        task_instruction=MODELS["retriever"].task_instruction[:100] + "..."
    )


def _create_qwen_retriever(model_path: str):
    """Create QwenRetriever in thread pool (blocking operation)."""
    return QwenRetriever(
        model_name=model_path,
        device=settings.device,
        max_length=settings.max_sequence_length,
        cache_dir=None,
        use_cache=False,
        with_instruction=True
    )


async def _load_reranker(s3_client):
    """Load ModernBERT reranker."""
    reranker_path = Path(settings.model_dir) / settings.reranker_model_path

    if not reranker_path.exists():
        logger.info("Downloading reranker model from S3")
        await download_model_from_s3(
            s3_client,
            f"{settings.s3_models_prefix}/{settings.reranker_model_path}/",
            reranker_path
        )
    else:
        logger.info("Reranker model found locally, skipping download")

    logger.info("Loading reranker")

    loop = asyncio.get_event_loop()
    reranker = await loop.run_in_executor(
        _executor,
        _create_reranker,
        str(reranker_path)
    )
    MODELS["reranker"] = reranker

    logger.info(
        "Reranker loaded successfully",
        model_type="ModernBERTReranker"
    )


def _create_reranker(model_path: str):
    """Create ModernBERTReranker in thread pool (blocking operation)."""
    return ModernBERTReranker(
        model_name=model_path,
        device=settings.device
    )


async def download_model_from_s3(s3_client, s3_prefix: str, local_path: Path):
    """
    Download all files from S3 prefix to local path.

    Args:
        s3_client: Boto3 S3 client
        s3_prefix: S3 prefix (e.g., "models/qwen-embedding-8b/")
        local_path: Local directory path
    """
    loop = asyncio.get_event_loop()

    file_count, total_size = await loop.run_in_executor(
        _executor,
        _sync_download_from_s3,
        s3_client,
        s3_prefix,
        local_path
    )

    logger.info(
        "Model download complete",
        files_downloaded=file_count,
        total_size_mb=round(total_size / (1024 * 1024), 2),
        local_path=str(local_path)
    )


def _sync_download_from_s3(s3_client, s3_prefix: str, local_path: Path) -> tuple:
    """
    Synchronous S3 download - runs in thread pool.
    """
    os.makedirs(local_path, exist_ok=True)

    file_count = 0
    total_size = 0
    last_checkpoint_gb = 0

    progress_logger.info(f"[S3] Starting download from s3://{settings.s3_bucket}/{s3_prefix}")

    paginator = s3_client.get_paginator("list_objects_v2")

    # First pass: count files
    total_files = 0
    expected_size = 0
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=s3_prefix):
        if "Contents" not in page:
            continue
        for obj in page["Contents"]:
            relative_path = obj["Key"][len(s3_prefix):]
            if relative_path:
                total_files += 1
                expected_size += obj["Size"]

    progress_logger.info(
        f"[S3] Found {total_files} files to download ({round(expected_size / (1024**3), 2)} GB)"
    )
    sys.stdout.flush()

    # Second pass: download files
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=s3_prefix):
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            key = obj["Key"]
            size = obj["Size"]

            relative_path = key[len(s3_prefix):]
            if not relative_path:
                continue

            local_file = local_path / relative_path
            local_file.parent.mkdir(parents=True, exist_ok=True)

            size_mb = round(size / (1024 * 1024), 2)
            progress_logger.info(
                f"[S3] Downloading {file_count + 1}/{total_files}: {relative_path} ({size_mb} MB)"
            )
            sys.stdout.flush()

            s3_client.download_file(
                settings.s3_bucket,
                key,
                str(local_file)
            )

            file_count += 1
            total_size += size

            progress_logger.info(f"[S3] Completed {file_count}/{total_files}: {relative_path}")
            sys.stdout.flush()

            # Log checkpoint every 1GB
            current_gb = total_size // (1024**3)
            if current_gb > last_checkpoint_gb:
                progress_pct = round(100 * total_size / expected_size, 1)
                progress_logger.info(
                    f"[S3] CHECKPOINT: {current_gb} GB downloaded ({progress_pct}% complete)"
                )
                sys.stdout.flush()
                last_checkpoint_gb = current_gb

    progress_logger.info(
        f"[S3] Download finished: {file_count} files, {round(total_size / (1024**3), 2)} GB total"
    )
    sys.stdout.flush()

    return file_count, total_size


def cleanup_models():
    """Cleanup models on shutdown."""
    logger.info("Cleaning up models")
    MODELS.clear()

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except:
        pass

    _executor.shutdown(wait=False)

    logger.info("Models cleaned up")
