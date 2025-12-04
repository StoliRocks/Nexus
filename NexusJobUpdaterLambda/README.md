# NexusJobUpdaterLambda

Lambda handler for updating job status after Step Functions workflow completion. This is the final task in the mapping workflow that writes results or errors to the Jobs table.

## Overview

The Job Updater Lambda:
1. Receives workflow results from Step Functions
2. Merges mapping results with reasoning
3. Updates job record to COMPLETED or FAILED status

## Architecture

```
Step Functions → Job Updater Lambda → DynamoDB Jobs Table
     ↓
  On Success: status=COMPLETED, mappings with reasoning
  On Error:   status=FAILED, error_message
```

## API

### Input Event Format (Success)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "mappings": [
    {
      "target_control_id": "NIST-SP-800-53#R5#AC-1",
      "target_framework": "NIST-SP-800-53",
      "similarity_score": 0.87,
      "rerank_score": 0.92
    }
  ],
  "reasoning": [
    {
      "control_id": "NIST-SP-800-53#R5#AC-1",
      "reasoning": "Both controls address access management..."
    }
  ]
}
```

### Input Event Format (Failure)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "error": {
    "Error": "EnrichmentError",
    "Cause": "NexusStrandsAgentService unavailable"
  }
}
```

### Output Format (Success)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "mapping_count": 5
}
```

### Output Format (Failure)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "error": "NexusStrandsAgentService unavailable"
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JOB_TABLE_NAME` | DynamoDB jobs table | Required |

## Job Record Updates

### COMPLETED Status

Updates the job record with:
- `status`: "COMPLETED"
- `updated_at`: Current timestamp
- `completed_at`: Current timestamp
- `mappings`: Array of enriched mappings with reasoning

### FAILED Status

Updates the job record with:
- `status`: "FAILED"
- `updated_at`: Current timestamp
- `failed_at`: Current timestamp
- `error_message`: Error description

## Mapping Enrichment

The service merges mapping results with reasoning:

```python
# Input mappings from ScienceOrchestrator
mappings = [
    {"target_control_id": "AC-1", "similarity_score": 0.87, "rerank_score": 0.92}
]

# Input reasoning from ReasoningAgent
reasoning = [
    {"control_id": "AC-1", "reasoning": "Both controls address..."}
]

# Output enriched mappings
enriched = [
    {
        "target_control_id": "AC-1",
        "similarity_score": 0.87,
        "rerank_score": 0.92,
        "reasoning": "Both controls address..."
    }
]
```

## Step Functions Integration

This Lambda is invoked at the end of the workflow:

```
Start → ValidateControl → CheckEnrichment → [RunEnrichment] → ScienceModel → Map(Reasoning) → JobUpdater → End
                                                                                                    ↓
                                                                              OnError → JobUpdater(FAILED)
```

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

Tests use moto for DynamoDB mocking.

```bash
# Run all tests
brazil-build test

# Run specific test
brazil-build test --addopts="-k test_update_job_completed"
```

## Dependencies

- `nexus-application-commons`: Shared utilities
- `boto3`: AWS SDK for DynamoDB operations
