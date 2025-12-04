# NexusMappingReviewAPIHandlerLambda

AWS Lambda handler for Mapping Review operations in the Nexus compliance control mapping pipeline.

## Overview

This Lambda manages expert reviews of control mappings for quality assurance. Reviews allow subject matter experts to validate or correct AI-generated mappings, providing human oversight of the ML pipeline.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mappings/{mappingId}/reviews` | List reviews for a mapping |
| POST | `/api/v1/mappings/{mappingId}/reviews` | Create a review |
| PUT | `/api/v1/mappings/{mappingId}/reviews/{reviewId}` | Update a review |

## Request/Response Examples

### List Reviews

```bash
GET /api/v1/mappings/AWS-IAM%231.0%23IAM.1%7CNIST-SP-800-53%23R5%23AC-1/reviews?maxResults=50
```

**Response:**
```json
{
  "reviews": [
    {
      "mappingKey": "AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-1",
      "reviewKey": "user@example.com#550e8400-e29b-41d4-a716-446655440000",
      "reviewId": "550e8400-e29b-41d4-a716-446655440000",
      "reviewerId": "user@example.com",
      "correct": true,
      "isFinalReview": false,
      "feedback": {
        "comment": "Mapping is accurate"
      },
      "submittedAt": "2024-01-15T10:30:00Z"
    }
  ],
  "nextToken": "..."
}
```

### Create Review

```bash
POST /api/v1/mappings/AWS-IAM%231.0%23IAM.1%7CNIST-SP-800-53%23R5%23AC-1/reviews
Content-Type: application/json

{
  "reviewerId": "user@example.com",
  "correct": true,
  "isFinalReview": false,
  "feedback": {
    "comment": "Mapping correctly identifies access control alignment",
    "confidence": "high"
  }
}
```

**Response (201 Created):**
```json
{
  "mappingKey": "AWS-IAM#1.0#IAM.1|NIST-SP-800-53#R5#AC-1",
  "reviewKey": "user@example.com#550e8400-e29b-41d4-a716-446655440000",
  "reviewId": "550e8400-e29b-41d4-a716-446655440000",
  "reviewerId": "user@example.com",
  "correct": true,
  "submittedAt": "2024-01-15T10:30:00Z",
  "submittedBy": {"system": "api"}
}
```

### Update Review

```bash
PUT /api/v1/mappings/{mappingId}/reviews/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "correct": false,
  "feedback": {
    "comment": "Upon further review, this mapping is too broad",
    "suggestedAlternative": "NIST-AC-2"
  },
  "isFinalReview": true
}
```

## Query Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `maxResults` | Maximum items per page (1-100) | 50 |
| `nextToken` | Pagination token | None |

## Database Schema

**Table:** `MappingReviews` (env: `REVIEWS_TABLE_NAME`)

| Attribute | Type | Description |
|-----------|------|-------------|
| `mappingKey` | String (PK) | Associated mapping key |
| `reviewKey` | String (SK) | `{reviewerId}#{reviewId}` |
| `reviewId` | String | UUID for this review |
| `reviewerId` | String | Person reviewing (required) |
| `correct` | Boolean | True if mapping is accurate (required) |
| `isFinalReview` | Boolean | Flag for final decision |
| `feedback` | Map | Additional comments/details |
| `submittedAt` | String | ISO timestamp |
| `submittedBy` | Map | Actor context |
| `updatedAt` | String | Last update timestamp |

## Request Body Fields

### Create Review (POST)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reviewerId` | String | Yes | Unique identifier for reviewer |
| `correct` | Boolean | Yes | Whether mapping is accurate |
| `isFinalReview` | Boolean | No | Mark as final decision (default: false) |
| `feedback` | Object | No | Additional comments |

### Update Review (PUT)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `correct` | Boolean | No | Updated accuracy assessment |
| `feedback` | Object | No | Updated comments |
| `isFinalReview` | Boolean | No | Updated final status |

At least one field must be provided for updates.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REVIEWS_TABLE_NAME` | DynamoDB table name | `MappingReviews` |

## Handler Entry Points

```python
from nexus_mapping_review_api_handler_lambda.handler import lambda_handler

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
brazil-build test --addopts="-k test_create_review"
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
    └─ service.py (ReviewService)
        │
        ├─ list_reviews()
        ├─ create_review()
        └─ update_review()
```

## Validation Rules

- `reviewerId` is required when creating a review
- `correct` field is required for new reviews
- Update must include at least one changed field
- Reviews are sorted by most recent first (ScanIndexForward: False)

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Missing required fields or invalid data |
| 404 | Review not found |
| 500 | Internal server error |

## Documentation

Generated documentation for the latest released version can be accessed here:
https://devcentral.amazon.com/ac/brazil/package-master/package/go/documentation?name=NexusMappingReviewAPIHandlerLambda&interface=1.0&versionSet=live
