# NexusFrameworkAPIHandlerLambda

AWS Lambda handler for Framework CRUD operations in the Nexus compliance control mapping pipeline.

## Overview

This Lambda manages compliance frameworks (NIST, SOC2, PCI-DSS, etc.) with support for versioning, archiving, and metadata management.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/frameworks` | List all frameworks |
| GET | `/api/v1/frameworks/{frameworkName}` | List versions of a framework |
| GET | `/api/v1/frameworks/{frameworkName}/{frameworkVersion}` | Get specific framework |
| PUT | `/api/v1/frameworks/{frameworkName}/{frameworkVersion}` | Create or update framework |
| POST | `/api/v1/frameworks/{frameworkName}/{frameworkVersion}/archive` | Archive framework |

## Request/Response Examples

### List Frameworks

```bash
GET /api/v1/frameworks?status=ACTIVE&maxResults=50
```

**Response:**
```json
{
  "frameworks": [
    {
      "frameworkName": "NIST-SP-800-53",
      "version": "R5",
      "frameworkKey": "NIST-SP-800-53#R5",
      "status": "ACTIVE",
      "description": "Security and Privacy Controls",
      "arn": "arn:aws:nexus:::framework/NIST-SP-800-53#R5"
    }
  ],
  "nextToken": "..."
}
```

### Create/Update Framework

```bash
PUT /api/v1/frameworks/NIST-SP-800-53/R5
Content-Type: application/json

{
  "description": "Security and Privacy Controls for Information Systems",
  "source": "NIST",
  "uri": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
  "additionalInfo": {
    "category": "federal"
  }
}
```

**Response (201 Created):**
```json
{
  "frameworkName": "NIST-SP-800-53",
  "version": "R5",
  "frameworkKey": "NIST-SP-800-53#R5",
  "status": "ACTIVE",
  "arn": "arn:aws:nexus:::framework/NIST-SP-800-53#R5",
  "createdBy": {"system": "api"},
  "createdAt": "2024-01-15T10:30:00Z"
}
```

## Query Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `status` | Filter by ACTIVE or ARCHIVED | All |
| `maxResults` | Maximum items per page (1-100) | 100 |
| `nextToken` | Pagination token | None |

## Database Schema

**Table:** `Frameworks` (env: `FRAMEWORKS_TABLE_NAME`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `frameworkName` | String (PK) | Framework identifier |
| `version` | String (SK) | Version identifier |
| `frameworkKey` | String | `{frameworkName}#{version}` |
| `status` | String | ACTIVE or ARCHIVED |
| `description` | String | Framework description |
| `source` | String | Issuing organization |
| `uri` | String | Reference URL |
| `additionalInfo` | Map | Custom metadata |
| `createdBy` | Map | Creator context |
| `createdAt` | String | ISO timestamp |
| `lastModifiedBy` | Map | Last modifier |
| `lastModifiedAt` | String | Last modification |
| `arn` | String | AWS ARN |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FRAMEWORKS_TABLE_NAME` | DynamoDB table name | `Frameworks` |

## Handler Entry Points

```python
from nexus_framework_api_handler_lambda.handler import lambda_handler

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
brazil-build test --addopts="-k test_list_frameworks"
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
    └─ service.py (FrameworkService)
        │
        ├─ list_frameworks()
        ├─ list_framework_versions()
        ├─ get_framework()
        ├─ create_or_update_framework()
        └─ archive_framework()
```

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Invalid request body or parameters |
| 404 | Framework not found |
| 500 | Internal server error |

All error responses follow the format:
```json
{
  "error": "Error message",
  "field": "optional_field_name"
}
```

## Documentation

Generated documentation for the latest released version can be accessed here:
https://devcentral.amazon.com/ac/brazil/package-master/package/go/documentation?name=NexusFrameworkAPIHandlerLambda&interface=1.0&versionSet=live
