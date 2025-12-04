# NexusLambdaAuthorizer

AWS Lambda custom authorizer for API Gateway in the Nexus compliance control mapping pipeline.

## Overview

This Lambda provides authentication and authorization for all Nexus API endpoints. It supports both Midway token authentication (for human users) and IAM principal authentication (for services/automation).

## Authentication Methods

### 1. Midway Token (Human Users)

```bash
curl -H "Authorization: Bearer <midway-token>" \
  https://api.nexus.example.com/api/v1/frameworks
```

- Validates token via AWS Midway service
- Extracts employee ID as principal
- Returns `ActorType.USER`

### 2. IAM Principal (Services)

```bash
# Using AWS Signature V4
aws-curl https://api.nexus.example.com/api/v1/frameworks
```

- Extracts principal from `requestContext.identity.userArn`
- Validates ARN format
- Returns `ActorType.SERVICE`

## Authorization Flow

```
API Gateway Request
       │
       ▼
┌─────────────────────────────┐
│   NexusLambdaAuthorizer     │
│                             │
│  1. Detect auth type        │
│     (Midway vs IAM)         │
│                             │
│  2. Validate credentials    │
│     - Midway: token         │
│     - IAM: ARN format       │
│                             │
│  3. Check BRASS Bindle Lock │
│     - SA bindle lock        │
│     - QA bindle lock        │
│                             │
│  4. Generate IAM policy     │
│     - Allow or Deny         │
└─────────────────────────────┘
       │
       ▼
   IAM Policy Document
   + Auth Context
```

## Response Format

### Allow Policy

```json
{
  "principalId": "user@example.com",
  "policyDocument": {
    "Version": "2012-10-17",
    "Statement": [{
      "Action": "execute-api:Invoke",
      "Effect": "Allow",
      "Resource": "arn:aws:execute-api:us-east-1:123456789:abc123/*"
    }]
  },
  "context": {
    "actor": {
      "actorId": "user@example.com",
      "actorType": "USER"
    },
    "persona": "SA"
  }
}
```

### Deny Policy

```json
{
  "principalId": "unknown",
  "policyDocument": {
    "Version": "2012-10-17",
    "Statement": [{
      "Action": "execute-api:Invoke",
      "Effect": "Deny",
      "Resource": "*"
    }]
  }
}
```

## Personas

| Persona | Description | Bindle Lock ID |
|---------|-------------|----------------|
| `SA` | Service Account / Admin | `nexus_bindle_lock_id_sa` |
| `QA` | Quality Assurance | `nexus_bindle_lock_id_qa` |

Persona assignment is determined by BRASS Bindle Lock membership.

## Models

### ActorContext

```python
class ActorContext:
    actorId: str      # User email or service ARN
    actorType: str    # "USER" or "SERVICE"
```

### AuthContext

```python
class AuthContext:
    actor: ActorContext
    resource: ResourceContext
    persona: str      # "SA" or "QA"
    authType: str     # "MIDWAY" or "IAM"
```

### AuthorizationResponse

```python
class AuthorizationResponse:
    principalId: str
    policyDocument: dict  # IAM policy
    context: dict         # Auth context (optional)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REGION` | BRASS region | `iad` |
| `STAGE` | Deployment stage | `beta` |

## Handler Entry Points

```python
from nexus_lambda_authorizer.handler import lambda_handler
```

## BRASS Integration

The authorizer integrates with Amazon BRASS (Bindle Resource Access Security Service) for authorization:

1. **BrassGateway**: Connects to BRASS service using stage and region
2. **BindleLockAuthorizer**: Checks Bindle Lock access
3. **BindleLockAuthorizationStrategy**: Implements authorization logic

## Development

### Build

```bash
brazil-build
```

### Test

```bash
brazil-build test
brazil-build test --addopts="-k test_midway_auth"
```

### Code Quality

```bash
brazil-build format      # black + isort
brazil-build mypy        # Type checking
brazil-build lint        # flake8
```

## Dependencies

- `boto3` - AWS SDK
- `aws-lambda-powertools` - Structured logging
- Custom BRASS authorization modules

## Architecture

```
handler.py (lambda_handler)
    │
    ├─ custom_authorizer.py
    │   ├─ detect_auth_type()
    │   ├─ validate_midway_token()
    │   └─ validate_iam_principal()
    │
    └─ authorization/
        └─ authorizer/
            └─ brass/
                ├─ bindle_lock_authorizer.py
                └─ bindle_lock_strategy.py
```

## Error Handling

| Exception | Condition | Result |
|-----------|-----------|--------|
| `UnauthorizedException` | No token, invalid token, not in bindle lock | Deny policy |
| `BadRequestException` | Invalid ARN format, missing principal | Deny policy |
| Any other exception | Unexpected error | Deny policy |

All errors result in a Deny policy being returned to API Gateway.

## Security Considerations

1. **Token Validation**: Midway tokens are validated against AWS Midway service
2. **ARN Validation**: IAM ARNs are validated for proper format
3. **Bindle Lock**: Access controlled via BRASS Bindle Lock membership
4. **Fail Closed**: Any error results in access denial

## Documentation

Generated documentation for the latest released version can be accessed here:
https://devcentral.amazon.com/ac/brazil/package-master/package/go/documentation?name=NexusLambdaAuthorizer&interface=1.0&versionSet=live
