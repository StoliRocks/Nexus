# NexusSqsTriggerLambda

Lambda function that consumes mapping requests from SQS and starts Step Functions workflows.

## Purpose

This Lambda provides a durable layer between the API and Step Functions:
- Receives mapping requests from `MappingRequestQueue`
- Starts Step Functions workflow execution
- Updates job status to RUNNING
- On failure, messages return to SQS for retry or move to DLQ

## Architecture

```
POST /api/v1/mappings
        │
        ▼
┌──────────────────────┐
│ AsyncAPIHandler      │ Creates job, sends to SQS
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ MappingRequestQueue  │ SQS Queue (durable)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ SqsTriggerLambda     │ ← This Lambda
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ Step Functions       │ Mapping workflow
└──────────────────────┘
        │
        ▼ (on failure, after 3 retries)
┌──────────────────────┐
│ MappingRequestDLQ    │ Dead Letter Queue
└──────────────────────┘
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STATE_MACHINE_ARN` | Yes | - | ARN of the mapping Step Functions state machine |
| `JOB_TABLE_NAME` | No | `MappingJobs` | DynamoDB table for job records |

## SQS Message Format

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
    "target_framework_key": "NIST-SP-800-53#R5",
    "target_control_ids": ["AC-1", "AC-2"]
}
```

## Error Handling

- **Malformed messages** (missing required fields, invalid JSON): Logged and discarded
- **Step Functions errors**: Message returns to queue for retry (max 3 attempts)
- **Execution already exists**: Treated as success (idempotent)
- **After 3 failures**: Message moves to DLQ for manual investigation

## Retry Behavior

The SQS queue is configured with:
- `maxReceiveCount: 3` - Messages retry up to 3 times before moving to DLQ
- `visibilityTimeout: 6 minutes` - 6x Lambda timeout for safety

## Handler Entry Point

```python
nexus_sqs_trigger_lambda.handler.lambda_handler
```

## Testing

```bash
brazil-build test
brazil-build test --addopts="-k test_pattern"
```
