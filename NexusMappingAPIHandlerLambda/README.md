# NexusMappingAPIHandlerLambda

AWS Lambda handler for Mapping CRUD operations in the Nexus compliance control mapping pipeline.

## Overview

This Lambda manages mappings between source and target controls across different compliance frameworks. Mappings represent the semantic relationship between AWS controls and framework controls (NIST, SOC2, PCI-DSS, etc.).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mappings` | List all mappings |
| GET | `/api/v1/mappings/{mappingId}` | Get specific mapping |
| GET | `/api/v1/controls/{controlId}/mappings` | Get mappings for a control |
| POST | `/api/v1/batchMappings` | Batch create mappings (max 100) |
| PUT | `/api/v1/mappings/{mappingId}/archive` | Archive mapping |

## Request/Response Examples

### List Mappings

```bash
GET /api/v1/mappings?status=ACTIVE&frameworkName=NIST-SP-800-53&maxResults=50
```

**Response:**
```json
{
  "mappings": [
    {
      "mappingKey": "AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-1",
      "sourceControlKey": "AWS-IAM#1.0#IAM.1",
      "targetControlKey": "NIST-SP-800-53#R5#AC-1",
      "status": "ACTIVE",
      "similarity_score": 0.85,
      "rerank_score": 0.92,
      "reasoning": "Both controls address access policy management..."
    }
  ],
  "nextToken": "..."
}
```

### Get Mappings for Control

```bash
GET /api/v1/controls/AWS-IAM%231.0%23IAM.1/mappings?status=ACTIVE
```

### Batch Create Mappings

```bash
POST /api/v1/batchMappings
Content-Type: application/json

{
  "mappings": [
    {
      "sourceControlKey": "AWS-IAM#1.0#IAM.1",
      "targetControlKey": "NIST-SP-800-53#R5#AC-1",
      "similarity_score": 0.85,
      "rerank_score": 0.92,
      "reasoning": "Access control policy alignment"
    },
    {
      "sourceControlKey": "AWS-IAM#1.0#IAM.1",
      "targetControlKey": "NIST-SP-800-53#R5#AC-2",
      "similarity_score": 0.78,
      "rerank_score": 0.85
    }
  ]
}
```

**Response (202 Accepted):**
```json
{
  "created": [
    {"mappingKey": "AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-1"},
    {"mappingKey": "AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-2"}
  ],
  "errors": []
}
```

### Archive Mapping

```bash
PUT /api/v1/mappings/AWS-IAM%231.0%23IAM.1%7CNIST-SP-800-53%23R5%23AC-1/archive
```

## Query Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `status` | Filter by ACTIVE or ARCHIVED | All |
| `frameworkName` | Filter by framework name | None |
| `frameworkVersion` | Filter by framework version | None |
| `control` | Filter by control ID | None |
| `maxResults` | Maximum items per page (1-100) | 100 |
| `nextToken` | Pagination token | None |

## Database Schema

**Table:** `ControlMappings` (env: `MAPPINGS_TABLE_NAME`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `mappingKey` | String (PK) | `{controlKey1}\|{controlKey2}` (sorted) |
| `sourceControlKey` | String | Source control key |
| `targetControlKey` | String | Target control key |
| `status` | String | ACTIVE or ARCHIVED |
| `similarity_score` | Number | Embedding similarity (0-1) |
| `rerank_score` | Number | Cross-encoder score (0-1) |
| `reasoning` | String | Human-readable rationale |
| `enrichment` | Map | Enriched control interpretation |
| `createdBy` | Map | Creator context |
| `createdAt` | String | ISO timestamp |
| `lastModifiedBy` | Map | Last modifier |
| `lastModifiedAt` | String | Last modification |

**Global Secondary Indexes:**
- `StatusIndex` - Query by status
- `MappingKeyIndex` - Query by mappingKey
- `ControlStatusIndex` - Query mappings for a specific control

## Key Format

The `mappingKey` is a deterministic composite key:
```
mappingKey = sorted([controlKey1, controlKey2]).join("|")
```

Example: `AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-1`

This ensures the same mapping can't be created twice in different orders.

## Batch Operations

- **Maximum Size:** 100 items per request
- **Response Code:** 202 ACCEPTED
- **Partial Success:** Returns both `created` and `errors` arrays
- **Deduplication:** Duplicate mappingKeys are rejected

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MAPPINGS_TABLE_NAME` | DynamoDB table name | `ControlMappings` |

## Handler Entry Points

```python
from nexus_mapping_api_handler_lambda.handler import lambda_handler

# Alias for CDK/BATS configuration
api_endpoint_handler = lambda_handler
```

## Development

### Build

```bash
brazil-build
```

### Test

```bash
brazil-build test
brazil-build test --addopts="-k test_batch_create"
```

### Code Quality

```bash
brazil-build format      # black + isort
brazil-build mypy        # Type checking
brazil-build lint        # flake8
```

## Dependencies

- `nexus_application_commons` - Response builders, DynamoDB utilities
- `boto3` - AWS SDK
- `pydantic` - Data validation

## Architecture

```
handler.py (lambda_handler)
    │
    ├─ Route by HTTP method and path
    │
    └─ service.py (MappingService)
        │
        ├─ list_mappings()
        ├─ get_mapping()
        ├─ get_mappings_for_control()
        ├─ batch_create_mappings()
        └─ archive_mapping()
```

## ML Scores

| Score | Description | Range |
|-------|-------------|-------|
| `similarity_score` | Cosine similarity from Qwen embeddings | 0.0 - 1.0 |
| `rerank_score` | Cross-encoder score from ModernBERT | 0.0 - 1.0 |

Higher scores indicate stronger semantic alignment between controls.

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Invalid request body or batch too large |
| 404 | Mapping not found |
| 409 | Duplicate mapping |
| 500 | Internal server error |

## Documentation

Generated documentation for the latest released version can be accessed here:
https://devcentral.amazon.com/ac/brazil/package-master/package/go/documentation?name=NexusMappingAPIHandlerLambda&interface=1.0&versionSet=live
