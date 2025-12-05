# NexusDlqRedriveLambda

Lambda function that redrives failed mapping requests from DLQ back to the main queue.

## Purpose

When mapping requests fail and land in the Dead Letter Queue (DLQ), this Lambda allows you to retry them after deploying a bug fix:

1. DLQ alarm triggers investigation
2. Team identifies and fixes the bug
3. Deploys fix to production
4. Invokes this Lambda to redrive failed requests

## Usage

### Manual Invocation (AWS Console or CLI)

```bash
# Redrive all messages (up to 100)
aws lambda invoke \
  --function-name NexusDlqRedriveLambda-prod \
  --payload '{}' \
  response.json

# Dry run to see message count
aws lambda invoke \
  --function-name NexusDlqRedriveLambda-prod \
  --payload '{"dry_run": true}' \
  response.json

# Limit number of messages to redrive
aws lambda invoke \
  --function-name NexusDlqRedriveLambda-prod \
  --payload '{"max_messages": 10}' \
  response.json
```

### Programmatic Invocation

```python
import boto3
import json

lambda_client = boto3.client('lambda')

response = lambda_client.invoke(
    FunctionName='NexusDlqRedriveLambda-prod',
    InvocationType='RequestResponse',
    Payload=json.dumps({'max_messages': 50}),
)

result = json.loads(response['Payload'].read())
print(f"Redriven {result['messages_redriven']} messages")
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DLQ_URL` | Yes | - | URL of the Dead Letter Queue |
| `MAIN_QUEUE_URL` | Yes | - | URL of the main MappingRequestQueue |
| `MAX_MESSAGES_PER_INVOCATION` | No | `100` | Default max messages to process |

## Event Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_messages` | int | 100 | Maximum messages to redrive |
| `dry_run` | bool | false | If true, just count messages |

## Response Format

```json
{
    "statusCode": 200,
    "messages_redriven": 45,
    "dlq_message_count_before": 50,
    "errors": null,
    "message": "Successfully redriven 45 messages"
}
```

### Status Codes

- `200`: All messages redriven successfully (or DLQ empty)
- `207`: Partial success (some messages failed)
- `500`: Configuration error

## Workflow

```
┌─────────────────────────────┐
│ DLQ Alarm Triggers          │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Team Investigates & Fixes   │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Deploy Fix to Production    │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Invoke DLQ Redrive Lambda   │◄── You are here
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Messages Flow Through       │
│ Fixed Pipeline              │
└─────────────────────────────┘
```

## Handler Entry Point

```python
nexus_dlq_redrive_lambda.handler.lambda_handler
```

## Testing

```bash
brazil-build test
brazil-build test --addopts="-k test_pattern"
```

## Best Practices

1. **Always dry run first** to understand the scope
2. **Redrive in batches** for large backlogs to monitor for issues
3. **Monitor CloudWatch** during redrive for new failures
4. **Keep DLQ alarm active** to catch any new failures
