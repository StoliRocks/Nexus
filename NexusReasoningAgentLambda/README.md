# NexusReasoningAgentLambda

Lambda handler for generating mapping reasoning in the Nexus control mapping system. This Lambda is invoked by Step Functions (in a Map state) to generate human-readable rationale for control mappings.

## Overview

The Reasoning Agent Lambda:
1. Receives mapping data from Step Functions Map state
2. Calls NexusStrandsAgentService `/reason` endpoint
3. Returns reasoning text for the mapping

## Architecture

```
Step Functions Map State → Reasoning Agent Lambda → NexusStrandsAgentService /reason
     (max 5 concurrent)
```

## API

### Input Event Format

```json
{
  "source_control_id": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "source_text": "Ensure API Gateway caching is enabled for improved performance.",
  "mapping": {
    "target_control_id": "NIST-SP-800-53#R5#AC-1",
    "target_control_key": "NIST-SP-800-53#R5#AC-1",
    "target_framework": "NIST-SP-800-53",
    "target_framework_key": "NIST-SP-800-53#R5",
    "text": "Access control policy and procedures...",
    "similarity_score": 0.87,
    "rerank_score": 0.92
  }
}
```

### Output Format

```json
{
  "control_id": "NIST-SP-800-53#R5#AC-1",
  "reasoning": "Both controls address access management. The AWS control ensures...",
  "source_control_id": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "status": "success"
}
```

### Error Response

```json
{
  "control_id": "NIST-SP-800-53#R5#AC-1",
  "error": "Error message",
  "source_control_id": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "status": "error"
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STRANDS_SERVICE_ENDPOINT` | NexusStrandsAgentService URL | Required |

## Reasoning Process

1. **Extract Mapping Data**: Gets source and target control information
2. **Build Request**: Formats request for NexusStrandsAgentService
3. **Call Strands Service**: Invokes reasoning generation
4. **Return Response**: Returns reasoning to Step Functions

## NexusStrandsAgentService Integration

The Lambda calls the `/api/v1/reason` endpoint:

```json
POST /api/v1/reason
{
  "sourceControlId": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "sourceText": "Ensure API Gateway caching is enabled...",
  "mapping": {
    "targetControlId": "NIST-SP-800-53#R5#AC-1",
    "targetFramework": "NIST-SP-800-53",
    "text": "Access control policy and procedures...",
    "similarityScore": 0.87,
    "rerankScore": 0.92
  }
}
```

Response:
```json
{
  "sourceControlId": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetControlId": "NIST-SP-800-53#R5#AC-1",
  "reasoning": "Both controls address access management...",
  "status": "success"
}
```

## Step Functions Integration

This Lambda runs in a Map state with max 5 concurrent executions:

```json
{
  "Type": "Map",
  "ItemsPath": "$.mappings",
  "MaxConcurrency": 5,
  "Iterator": {
    "StartAt": "GenerateReasoning",
    "States": {
      "GenerateReasoning": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:...:NexusReasoningAgentLambda",
        "End": true
      }
    }
  }
}
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

Tests use mock responses for NexusStrandsAgentService.

```bash
# Run all tests
brazil-build test

# Run specific test
brazil-build test --addopts="-k test_generate_reasoning"
```

## Dependencies

- `nexus-application-commons`: Shared utilities
- `urllib3`: HTTP client for NexusStrandsAgentService calls
