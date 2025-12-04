# NexusMappingFeedbackAPIHandlerLambda

AWS Lambda handler for Mapping Feedback operations in the Nexus compliance control mapping pipeline.

## Overview

This Lambda collects user thumbs-up/thumbs-down feedback on mappings. Unlike reviews (which are detailed expert assessments), feedback provides quick user sentiment signals that can be used to improve the ML models over time.

**Key Constraint:** One feedback per user per mapping. Users must use PUT to update existing feedback.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mappings/{mappingId}/feedbacks` | List feedbacks for a mapping |
| POST | `/api/v1/mappings/{mappingId}/feedbacks` | Create feedback |
| PUT | `/api/v1/mappings/{mappingId}/feedbacks/{feedbackId}` | Update feedback |

## Request/Response Examples

### List Feedbacks

```bash
GET /api/v1/mappings/AWS-IAM%231.0%23IAM.1%7CNIST-SP-800-53%23R5%23AC-1/feedbacks?maxResults=50
```

**Response:**
```json
{
  "feedbacks": [
    {
      "mappingKey": "AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-1",
      "feedbackProviderId": "user@example.com",
      "label": "thumbs_up",
      "decision": true,
      "feedback": {
        "comment": "This mapping is helpful"
      },
      "submittedAt": "2024-01-15T10:30:00Z"
    }
  ],
  "nextToken": "..."
}
```

### Create Feedback

```bash
POST /api/v1/mappings/AWS-IAM%231.0%23IAM.1%7CNIST-SP-800-53%23R5%23AC-1/feedbacks
Content-Type: application/json

{
  "feedbackProviderId": "user@example.com",
  "label": "thumbs_up",
  "feedback": {
    "comment": "This mapping helped me understand the control relationship"
  }
}
```

**Response (201 Created):**
```json
{
  "mappingKey": "AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-1",
  "feedbackProviderId": "user@example.com",
  "label": "thumbs_up",
  "decision": true,
  "submittedAt": "2024-01-15T10:30:00Z",
  "submittedBy": {"system": "api"}
}
```

### Update Feedback

```bash
PUT /api/v1/mappings/{mappingId}/feedbacks/user@example.com
Content-Type: application/json

{
  "label": "thumbs_down",
  "feedback": {
    "comment": "Changed my mind after reviewing more closely"
  }
}
```

## Query Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `maxResults` | Maximum items per page (1-100) | 50 |
| `nextToken` | Pagination token | None |

## Database Schema

**Table:** `MappingFeedbacks` (env: `FEEDBACKS_TABLE_NAME`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `mappingKey` | String (PK) | Associated mapping key |
| `reviewerId` | String (SK) | Same as feedbackProviderId (ensures uniqueness) |
| `feedbackProviderId` | String | User identifier (required) |
| `label` | String | `thumbs_up` or `thumbs_down` (required) |
| `decision` | Boolean | Computed: true if thumbs_up, false if thumbs_down |
| `feedback` | Map | Additional comments |
| `submittedAt` | String | ISO timestamp |
| `submittedBy` | Map | Actor context |

## Request Body Fields

### Create Feedback (POST)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `feedbackProviderId` | String | Yes | Unique user identifier |
| `label` | String | Yes | Must be `thumbs_up` or `thumbs_down` |
| `feedback` | Object | No | Additional comments |

### Update Feedback (PUT)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | String | No | Updated label (`thumbs_up` or `thumbs_down`) |
| `feedback` | Object | No | Updated comments |

At least one field must be provided for updates.

## Label Values

| Label | Decision | Meaning |
|-------|----------|---------|
| `thumbs_up` | `true` | User finds mapping helpful/accurate |
| `thumbs_down` | `false` | User finds mapping unhelpful/inaccurate |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FEEDBACKS_TABLE_NAME` | DynamoDB table name | `MappingFeedbacks` |

## Handler Entry Points

```python
from nexus_mapping_feedback_api_handler_lambda.handler import lambda_handler

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
brazil-build test --addopts="-k test_create_feedback"
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
    └─ service.py (FeedbackService)
        │
        ├─ list_feedbacks()
        ├─ create_feedback()
        └─ update_feedback()
```

## Validation Rules

- `feedbackProviderId` is required when creating feedback
- `label` must be exactly `thumbs_up` or `thumbs_down`
- One feedback per user per mapping (enforced by unique key)
- Duplicate feedback returns error - use PUT to update
- Update must include at least one changed field

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Missing required fields, invalid label, or duplicate feedback |
| 404 | Feedback not found |
| 409 | Feedback already exists for this user (use PUT to update) |
| 500 | Internal server error |

## Use Cases

1. **Quick User Sentiment**: Users can quickly indicate if a mapping is helpful
2. **ML Model Improvement**: Aggregate feedback can guide model retraining
3. **Quality Metrics**: Track user satisfaction with mapping quality
4. **Prioritization**: Low-rated mappings can be prioritized for expert review

## Documentation

Generated documentation for the latest released version can be accessed here:
https://devcentral.amazon.com/ac/brazil/package-master/package/go/documentation?name=NexusMappingFeedbackAPIHandlerLambda&interface=1.0&versionSet=live
