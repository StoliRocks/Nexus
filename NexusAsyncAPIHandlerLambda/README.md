# NexusAsyncAPIHandlerLambda

AWS Lambda handler for async mapping job creation. Handles `POST /api/v1/mappings` requests and starts Step Functions workflows.

## Overview

This Lambda:
1. Validates input (control_key format, framework_key format, target_control_ids)
2. Validates control and framework existence in DynamoDB
3. Creates a job record with PENDING status
4. Starts Step Functions workflow execution
5. Returns 202 Accepted with job details

## API

### POST /api/v1/mappings

Create a new mapping job.

**Request Body:**
```json
{
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5",
  "target_control_ids": ["AC-1", "AC-2"]  // optional
}
```

**Response (202 Accepted):**
```json
{
  "mappingId": "uuid-here",
  "status": "ACCEPTED",
  "statusUrl": "https://api.example.com/api/v1/mappings/uuid-here",
  "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetFrameworkKey": "NIST-SP-800-53#R5"
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JOB_TABLE_NAME` | DynamoDB table for job records | Yes |
| `STATE_MACHINE_ARN` | Step Functions state machine ARN | Yes |
| `FRAMEWORKS_TABLE_NAME` | DynamoDB table for frameworks | Yes |
| `CONTROLS_TABLE_NAME` | DynamoDB table for controls | Yes |

## Key Format

- **control_key**: `frameworkName#version#controlId` (e.g., `AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED`)
- **target_framework_key**: `frameworkName#version` (e.g., `NIST-SP-800-53#R5`)

## Dependencies

- `nexus_application_commons` - Response builders
- `pydantic` - Input validation
- `boto3` - AWS SDK

## Build

```bash
brazil-build
brazil-build test
```
