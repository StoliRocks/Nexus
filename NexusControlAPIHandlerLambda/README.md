# NexusControlAPIHandlerLambda

AWS Lambda handler for Control CRUD operations with batch support in the Nexus compliance control mapping pipeline.

## Overview

This Lambda manages controls within compliance frameworks, supporting individual and batch operations for efficient bulk data management.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/frameworks/{name}/{version}/controls` | List controls |
| GET | `/api/v1/frameworks/{name}/{version}/controls/{controlId}` | Get control |
| PUT | `/api/v1/frameworks/{name}/{version}/controls/{controlId}` | Create/update control |
| POST | `/api/v1/frameworks/{name}/{version}/batchControls` | Batch create (max 100) |
| PUT | `/api/v1/frameworks/{name}/{version}/controls/{controlId}/archive` | Archive control |
| POST | `/api/v1/frameworks/{name}/{version}/controls/batchArchive` | Batch archive (max 100) |

## Request/Response Examples

### List Controls

```bash
GET /api/v1/frameworks/NIST-SP-800-53/R5/controls?status=ACTIVE&maxResults=50
```

**Response:**
```json
{
  "controls": [
    {
      "frameworkKey": "NIST-SP-800-53#R5",
      "controlId": "AC-1",
      "controlKey": "NIST-SP-800-53#R5#AC-1",
      "title": "Access Control Policy and Procedures",
      "status": "ACTIVE",
      "arn": "arn:aws:nexus::control:NIST-SP-800-53#R5#AC-1"
    }
  ],
  "nextToken": "..."
}
```

### Create/Update Control

```bash
PUT /api/v1/frameworks/NIST-SP-800-53/R5/controls/AC-1
Content-Type: application/json

{
  "title": "Access Control Policy and Procedures",
  "description": "The organization develops, documents, and disseminates...",
  "controlGuide": "Implementation guidance...",
  "additionalInfo": {
    "family": "Access Control"
  }
}
```

### Batch Create Controls

```bash
POST /api/v1/frameworks/NIST-SP-800-53/R5/batchControls
Content-Type: application/json

{
  "controls": [
    {
      "controlId": "AC-1",
      "title": "Access Control Policy",
      "description": "..."
    },
    {
      "controlId": "AC-2",
      "title": "Account Management",
      "description": "..."
    }
  ]
}
```

**Response (202 Accepted):**
```json
{
  "created": [
    {"controlId": "AC-1", "controlKey": "NIST-SP-800-53#R5#AC-1"},
    {"controlId": "AC-2", "controlKey": "NIST-SP-800-53#R5#AC-2"}
  ],
  "errors": []
}
```

### Batch Archive Controls

```bash
POST /api/v1/frameworks/NIST-SP-800-53/R5/controls/batchArchive
Content-Type: application/json

{
  "controlIds": ["AC-1", "AC-2", "AC-3"]
}
```

## Query Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `status` | Filter by ACTIVE or ARCHIVED | All |
| `maxResults` | Maximum items per page (1-100) | 100 |
| `nextToken` | Pagination token | None |

## Database Schema

**Table:** `FrameworkControls` (env: `CONTROLS_TABLE_NAME`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `frameworkKey` | String (PK) | `{frameworkName}#{version}` |
| `controlKey` | String (SK) | `{frameworkKey}#{controlId}` |
| `controlId` | String | Control identifier |
| `controlVersion` | String | Semantic version (default: 1.0) |
| `status` | String | ACTIVE or ARCHIVED |
| `title` | String | Control title (required for create) |
| `description` | String | Control description |
| `controlGuide` | String | Implementation guidance |
| `additionalInfo` | Map | Custom metadata |
| `createdBy` | Map | Creator context |
| `createdAt` | String | ISO timestamp |
| `lastModifiedBy` | Map | Last modifier |
| `lastModifiedAt` | String | Last modification |
| `arn` | String | AWS ARN |

## Batch Operations

- **Maximum Size:** 100 items per request
- **Response Code:** 202 ACCEPTED
- **Partial Success:** Returns both `created` and `errors` arrays
- **Validation:** Framework must exist before batch operations

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTROLS_TABLE_NAME` | DynamoDB table name | `FrameworkControls` |

## Handler Entry Points

```python
from nexus_control_api_handler_lambda.handler import lambda_handler

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
    └─ service.py (ControlService)
        │
        ├─ list_controls()
        ├─ get_control()
        ├─ create_or_update_control()
        ├─ batch_create_controls()
        ├─ archive_control()
        └─ batch_archive_controls()
```

## Validation Rules

- `title` is required for new controls (optional for updates)
- Framework must exist before adding controls
- Cannot archive already archived controls
- Batch operations fail individual items without affecting others

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Invalid request body, missing title, or batch too large |
| 404 | Control or framework not found |
| 409 | Conflict (e.g., already archived) |
| 500 | Internal server error |

## Documentation

Generated documentation for the latest released version can be accessed here:
https://devcentral.amazon.com/ac/brazil/package-master/package/go/documentation?name=NexusControlAPIHandlerLambda&interface=1.0&versionSet=live
