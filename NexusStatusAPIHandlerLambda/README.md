# NexusStatusAPIHandlerLambda

AWS Lambda handler for mapping job status queries. Handles `GET /api/v1/mappings/{mappingId}` requests.

## Overview

This Lambda queries the Jobs DynamoDB table to return the current status of a mapping job, along with results if the job has completed.

## API

### GET /api/v1/mappings/{mappingId}

Get the status of a mapping job.

**Path Parameters:**
- `mappingId` (required): The job identifier returned from POST /api/v1/mappings

**Response (200 OK) - Pending/Running:**
```json
{
  "mappingId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RUNNING",
  "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetFrameworkKey": "NIST-SP-800-53#R5",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:05Z"
}
```

**Response (200 OK) - Completed:**
```json
{
  "mappingId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetFrameworkKey": "NIST-SP-800-53#R5",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:05:00Z",
  "result": {
    "mappings": [
      {
        "targetControlKey": "NIST-SP-800-53#R5#AC-1",
        "similarityScore": 0.92,
        "rerankScore": 0.95
      }
    ],
    "reasoning": {
      "NIST-SP-800-53#R5#AC-1": "Both controls address..."
    }
  }
}
```

**Response (200 OK) - Failed:**
```json
{
  "mappingId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetFrameworkKey": "NIST-SP-800-53#R5",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:02:00Z",
  "error": "Enrichment service unavailable"
}
```

**Response (404 Not Found):**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Mapping job '550e8400-e29b-41d4-a716-446655440000' not found"
  }
}
```

## Job Statuses

| Status | Description |
|--------|-------------|
| `PENDING` | Job created, waiting to start |
| `RUNNING` | Step Functions workflow in progress |
| `COMPLETED` | Workflow finished successfully with results |
| `FAILED` | Workflow failed with error message |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JOB_TABLE_NAME` | DynamoDB table for job records | Yes |

## Dependencies

- `nexus_application_commons` - Response builders
- `boto3` - AWS SDK

## Build

```bash
brazil-build
brazil-build test
```
