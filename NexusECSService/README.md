# NexusECSService

GPU-accelerated ML inference service for control mapping. Provides FastAPI endpoints for embedding generation, similarity retrieval, and cross-encoder reranking.

## Overview

This service runs on ECS with GPU instances (g5.12xlarge with 4x NVIDIA A10G GPUs) and provides:

- **Embedding Generation**: 4096-dimensional vectors using Qwen-embedding-8B
- **Similarity Retrieval**: Cosine similarity search with GPU-accelerated tensor operations
- **Reranking**: Cross-encoder scoring using ModernBERT

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/embed` | POST | Generate embedding for control text |
| `/api/v1/retrieve` | POST | Find top-K similar controls |
| `/api/v1/rerank` | POST | Rerank candidates using cross-encoder |
| `/health` | GET | Health check (returns 200 during model loading) |
| `/ready` | GET | Readiness check (returns 200 when models loaded) |

## Installation

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Or with Brazil
brazil-build
```

### Docker Build

```bash
# Build the image
docker build -t nexus-ecs-service .

# Run locally (requires GPU)
docker run --gpus all -p 8000:8000 \
  -e AWS_REGION=us-east-1 \
  -e MODEL_BUCKET=your-model-bucket \
  nexus-ecs-service
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for S3/DynamoDB | `us-east-1` |
| `MODEL_BUCKET` | S3 bucket containing models | Required |
| `RETRIEVER_MODEL_PATH` | S3 path to Qwen model | `models/qwen-embedding-8b/` |
| `RERANKER_MODEL_PATH` | S3 path to ModernBERT model | `models/modernbert-reranker/` |
| `EMBEDDING_CACHE_TABLE` | DynamoDB table for embeddings | `nexus-embedding-cache` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Usage Examples

### Generate Embedding

```python
import httpx

response = httpx.post("http://localhost:8000/api/v1/embed", json={
    "control_id": "IAM.21",
    "text": "Ensure IAM users are managed through centralized identity provider"
})

result = response.json()
# {
#   "control_id": "IAM.21",
#   "embedding": [0.123, -0.456, ...],  # 4096 floats
#   "cache_hit": false
# }
```

### Similarity Retrieval

```python
response = httpx.post("http://localhost:8000/api/v1/retrieve", json={
    "source_embedding": [...],  # 4096-dim normalized vector
    "target_embeddings": [
        [...],  # Target 1
        [...],  # Target 2
    ],
    "top_k": 50
})

result = response.json()
# {
#   "candidates": [
#     {"control_id": "0", "similarity": 0.95},
#     {"control_id": "1", "similarity": 0.87},
#     ...
#   ]
# }
```

### Rerank Candidates

```python
response = httpx.post("http://localhost:8000/api/v1/rerank", json={
    "source_text": "Ensure users authenticate with MFA",
    "candidates": [
        {"control_id": "CTRL-001", "text": "Enable MFA for all accounts"},
        {"control_id": "CTRL-002", "text": "Rotate access keys regularly"},
        {"control_id": "CTRL-003", "text": "Monitor failed login attempts"}
    ]
})

result = response.json()
# {
#   "rankings": [
#     {"control_id": "CTRL-001", "score": 0.92},
#     {"control_id": "CTRL-003", "score": 0.45},
#     {"control_id": "CTRL-002", "score": 0.23}
#   ]
# }
```

## Deployment

### ECS Task Definition

The service is deployed via CDK in `NexusApplicationPipelineCDK`. Key configuration:

```json
{
  "family": "nexus-ecs-service",
  "cpu": "16384",
  "memory": "65536",
  "requiresCompatibilities": ["EC2"],
  "containerDefinitions": [{
    "name": "nexus-ecs-service",
    "image": "${ECR_IMAGE}",
    "portMappings": [{"containerPort": 8000}],
    "resourceRequirements": [{
      "type": "GPU",
      "value": "4"
    }],
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "startPeriod": 120,
      "retries": 3
    }
  }]
}
```

### Health Check Strategy

- `/health` returns 200 immediately (allows ALB to route during model loading)
- `/ready` returns 503 until models are loaded, then 200
- Model loading happens in background after server starts
- Typical model loading time: 60-90 seconds

## Architecture

```
NexusECSService/
├── src/nexus_ecs_service/
│   ├── interfaces/           # Abstract base classes
│   │   ├── base_retriever.py # Retriever contract
│   │   └── base_reranker.py  # Reranker contract
│   ├── algorithms/           # ML model implementations
│   │   ├── retrievers/
│   │   │   └── qwen_retriever.py
│   │   └── rerankers/
│   │       └── modernbert_reranker.py
│   └── app/                  # FastAPI application
│       ├── main.py           # App entry point
│       ├── config.py         # Settings
│       ├── startup.py        # Model loading
│       ├── routers/          # API endpoints
│       └── services/         # Business logic
├── test/                     # Pytest tests
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=nexus_ecs_service --cov-report=html

# Run specific test file
pytest test/test_embed_router.py -v
```

## Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Embed (cache miss) | 50-100ms | ~20 req/s |
| Embed (cache hit) | <10ms | ~500 req/s |
| Retrieve (1K targets) | <50ms | ~50 req/s |
| Retrieve (10K targets) | <200ms | ~10 req/s |
| Rerank (50 candidates) | 2-3s | ~0.4 req/s |
| Rerank (100 candidates) | 4-5s | ~0.2 req/s |

## Dependencies

- Python 3.11+
- PyTorch 2.0+
- Transformers 4.35+
- FastAPI 0.104+
- sentence-transformers 2.2+
