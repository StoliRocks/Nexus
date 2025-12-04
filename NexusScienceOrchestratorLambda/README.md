# NexusScienceOrchestratorLambda

Lambda handler for ML pipeline orchestration in the Nexus control mapping system. This Lambda is invoked by Step Functions to perform embedding, retrieval, and reranking operations.

## Overview

The Science Orchestrator handles three main actions:
- **validate_control**: Verify source control exists in database
- **check_enrichment**: Check if enrichment data exists for a control
- **map_control**: Execute full mapping pipeline (embed → retrieve → rerank)

## Architecture

```
Step Functions → Science Orchestrator Lambda → ECS ML Service (NexusECSService)
                       ↓
                  DynamoDB Tables:
                  - Controls
                  - Frameworks
                  - Enrichment
                  - EmbeddingCache
```

## API

### Input Event Format

```json
{
  "action": "validate_control | check_enrichment | map_control",
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5",
  "target_control_ids": ["AC-1", "AC-2"]
}
```

### Actions

#### validate_control

Verify control exists in database.

**Input:**
```json
{
  "action": "validate_control",
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
}
```

**Output:**
```json
{
  "exists": true,
  "control": { ... },
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
}
```

#### check_enrichment

Check if enrichment data exists.

**Input:**
```json
{
  "action": "check_enrichment",
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
}
```

**Output:**
```json
{
  "exists": true,
  "enrichment": { "enriched_text": "..." }
}
```

#### map_control

Execute mapping pipeline.

**Input:**
```json
{
  "action": "map_control",
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5",
  "target_control_ids": ["AC-1", "AC-2", "AC-3"]
}
```

**Output:**
```json
{
  "mappings": [
    {
      "target_control_key": "NIST-SP-800-53#R5#AC-1",
      "target_control_id": "AC-1",
      "target_framework_key": "NIST-SP-800-53#R5",
      "similarity_score": 0.87,
      "rerank_score": 0.92,
      "text": "Access control policy..."
    }
  ],
  "source_control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5"
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTROLS_TABLE_NAME` | DynamoDB controls table | Required |
| `FRAMEWORKS_TABLE_NAME` | DynamoDB frameworks table | Required |
| `ENRICHMENT_TABLE_NAME` | DynamoDB enrichment cache table | Required |
| `EMBEDDING_CACHE_TABLE_NAME` | DynamoDB embedding cache table | Required |
| `SCIENCE_API_ENDPOINT` | ECS ML service URL | Required |
| `MODEL_VERSION` | Embedding model version | `v1` |
| `USE_MOCK_SCIENCE` | Use mock ML responses | `false` |

## Key Patterns

### Control Keys
- `controlKey`: `frameworkName#version#controlId`
- Example: `NIST-SP-800-53#R5#AC-1`, `AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED`

### Framework Keys
- `frameworkKey`: `frameworkName#version`
- Example: `NIST-SP-800-53#R5`, `AWS.ControlCatalog#1.0`

## Development

```bash
# Install dependencies
brazil-build

# Run tests
brazil-build test

# Format code
brazil-build format

# Type checking
brazil-build mypy
```

## Testing

Tests use moto for DynamoDB mocking and mock responses for the ECS ML service.

```bash
# Run all tests
brazil-build test

# Run specific test
brazil-build test --addopts="-k test_map_control"
```

## Dependencies

- `nexus-application-commons`: Response builders and utilities
- `boto3`: AWS SDK for DynamoDB operations
- `urllib3`: HTTP client for ECS ML service calls
