# NexusEnrichmentAgentLambda

Lambda handler for control enrichment in the Nexus control mapping system. This Lambda is invoked by Step Functions to enrich control text using the NexusStrandsAgentService multi-agent system.

## Overview

The Enrichment Agent Lambda:
1. Receives control data from Step Functions
2. Calls NexusStrandsAgentService `/enrich` endpoint
3. Stores enriched text in DynamoDB Enrichment table
4. Returns enrichment result to Step Functions

## Architecture

```
Step Functions → Enrichment Agent Lambda → NexusStrandsAgentService /enrich
                       ↓
                  DynamoDB Enrichment Table
```

## API

### Input Event Format

```json
{
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "control": {
    "title": "API Gateway Cache Enabled",
    "description": "Ensure API Gateway caching is enabled for improved performance.",
    "metadata": {
      "frameworkName": "AWS.ControlCatalog",
      "frameworkVersion": "1.0"
    }
  }
}
```

### Output Format

```json
{
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "enriched_text": "Enhanced control text with semantic richness...",
  "status": "success"
}
```

### Error Response

```json
{
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "error": "Error message",
  "status": "error"
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENRICHMENT_TABLE_NAME` | DynamoDB enrichment cache table | Required |
| `STRANDS_SERVICE_ENDPOINT` | NexusStrandsAgentService URL | Required |
| `ENRICHMENT_VERSION` | Version tag for enrichments | `v1` |

## Enrichment Process

1. **Extract Control Text**: Gets description, text, or title from control data
2. **Build Request**: Formats request for NexusStrandsAgentService
3. **Call Strands Service**: Invokes multi-agent enrichment system
4. **Store Result**: Caches enriched text in DynamoDB
5. **Return Response**: Returns enrichment result to Step Functions

## NexusStrandsAgentService Integration

The Lambda calls the `/api/v1/enrich` endpoint:

```json
POST /api/v1/enrich
{
  "metadata": {
    "frameworkName": "AWS.ControlCatalog",
    "frameworkVersion": "1.0"
  },
  "control": {
    "shortId": "API_GW_CACHE_ENABLED",
    "title": "API Gateway Cache Enabled",
    "description": "Ensure API Gateway caching is enabled..."
  }
}
```

Response:
```json
{
  "controlId": "API_GW_CACHE_ENABLED",
  "enrichedInterpretation": {
    "enrichedText": "...",
    "securityObjective": "...",
    "complianceContext": "..."
  },
  "status": "success"
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

Tests use moto for DynamoDB mocking and responses for HTTP mocking.

```bash
# Run all tests
brazil-build test

# Run specific test
brazil-build test --addopts="-k test_enrich_control"
```

## Dependencies

- `nexus-application-commons`: Shared utilities
- `boto3`: AWS SDK for DynamoDB operations
- `urllib3`: HTTP client for NexusStrandsAgentService calls
