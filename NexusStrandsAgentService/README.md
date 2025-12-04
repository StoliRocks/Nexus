# NexusStrandsAgentService

ECS service for strands-based agent execution, providing HTTP endpoints for control enrichment and mapping reasoning generation.

## Overview

This service wraps the `NexusEnrichmentAgent` and `NexusReasoningAgent` packages as a FastAPI application deployed on AWS ECS. It provides:

- **Control Enrichment**: Multi-agent system (5 specialized agents + master reviewer) for enriching compliance controls with AWS-mappable insights
- **Reasoning Generation**: Human-readable rationale for why AWS controls map to framework controls

## Architecture

```
NexusStrandsAgentService (ECS Container)
├── FastAPI Application
│   ├── /api/v1/enrich        → NexusEnrichmentAgent
│   ├── /api/v1/reason        → NexusReasoningAgent
│   └── /health, /ready       → Health checks
│
├── Dependencies
│   ├── NexusEnrichmentAgent  (strands-agents, Bedrock)
│   └── NexusReasoningAgent   (boto3, Bedrock)
│
└── Infrastructure
    └── AWS Bedrock (Claude models)
```

## API Endpoints

### Enrichment Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/enrich` | Enrich a single control |
| POST | `/api/v1/enrich/batch` | Batch enrich controls (max 10) |
| POST | `/api/v1/profile/generate` | Generate framework profile |

### Reasoning Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reason` | Generate reasoning for single mapping |
| POST | `/api/v1/reason/batch` | Batch reasoning (max 20) |
| POST | `/api/v1/reason/consolidated` | Consolidated reasoning (max 10, single API call) |

### Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (always 200) |
| GET | `/ready` | Readiness check (verifies dependencies) |
| GET | `/` | Service info and endpoint listing |
| GET | `/docs` | OpenAPI documentation |

## Usage Examples

### Enrich a Control

```python
import httpx

response = httpx.post("http://service:8000/api/v1/enrich", json={
    "metadata": {
        "frameworkName": "NIST-SP-800-53",
        "frameworkVersion": "R5"
    },
    "control": {
        "shortId": "AC-1",
        "title": "Access Control Policy",
        "description": "The organization develops, documents, and disseminates..."
    }
})
# Returns enriched interpretation with AWS service mappings
```

### Generate Framework Profile

```python
response = httpx.post("http://service:8000/api/v1/profile/generate", json={
    "frameworkName": "SOC-2",
    "sampleControls": [
        {"shortId": "CC1.1", "title": "Control Environment", "description": "..."},
        {"shortId": "CC1.2", "title": "Board Oversight", "description": "..."},
        {"shortId": "CC1.3", "title": "Management Philosophy", "description": "..."}
    ]
})
# Returns framework profile for enhanced enrichment
```

### Generate Mapping Reasoning

```python
response = httpx.post("http://service:8000/api/v1/reason", json={
    "sourceControlId": "AWS-IAM-001",
    "sourceText": "Ensure IAM policies are attached only to groups or roles",
    "mapping": {
        "targetControlId": "NIST-AC-1",
        "targetFramework": "NIST-SP-800-53",
        "text": "Access control policy and procedures",
        "similarityScore": 0.85,
        "rerankScore": 0.92
    }
})
# Returns human-readable rationale for the mapping
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | nexus-strands-agent-service | Service identifier |
| `ENVIRONMENT` | development | Deployment environment |
| `AWS_REGION` | us-east-1 | AWS region |
| `BEDROCK_MODEL_ID` | us.anthropic.claude-sonnet-4-5-20250929-v1:0 | Model for enrichment agents |
| `REASONING_MODEL_ID` | anthropic.claude-3-haiku-20240307-v1:0 | Model for reasoning |
| `BEDROCK_ROLE_ARN` | (optional) | Cross-account Bedrock access role |
| `LOG_LEVEL` | INFO | Logging level |

## Development

### Local Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Install internal packages
pip install -e ../NexusEnrichmentAgent
pip install -e ../NexusReasoningAgent

# Run locally
uvicorn nexus_strands_agent_service.app.main:app --reload --port 8000
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=nexus_strands_agent_service --cov-report=term-missing
```

### Building Docker Image

```bash
# Build image (from project root)
docker build -t nexus-strands-agent-service \
  -f NexusStrandsAgentService/Dockerfile \
  --build-context NexusEnrichmentAgent=NexusEnrichmentAgent \
  --build-context NexusReasoningAgent=NexusReasoningAgent \
  NexusStrandsAgentService
```

## Brazil Build

```bash
brazil-build
brazil-build test
brazil-build format
brazil-build mypy
brazil-build lint
```

## Deployment

This service is deployed to AWS ECS via the `NexusApplicationPipelineCDK` stack. See the CDK stack for infrastructure configuration.

## Dependencies

- **NexusEnrichmentAgent**: Multi-agent control enrichment (strands-agents)
- **NexusReasoningAgent**: Mapping rationale generation (boto3)
- **FastAPI**: HTTP API framework
- **AWS Bedrock**: Claude model access
