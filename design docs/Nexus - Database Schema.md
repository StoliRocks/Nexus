# Nexus Database Schema

## Overview

Nexus uses Amazon DynamoDB for its persistence layer. All tables use on-demand billing (PAY_PER_REQUEST) and are configured with point-in-time recovery enabled. Production tables have RETAIN removal policy while non-production tables use DESTROY.

## Table Summary

| Table Name | Purpose | Partition Key | Sort Key | Streams |
|------------|---------|---------------|----------|---------|
| Frameworks | Framework metadata and versions | frameworkName | version | No |
| FrameworkControls | Control definitions within frameworks | frameworkKey | controlKey | Yes |
| ControlMappings | Mappings between controls | controlKey | mappedControlKey | Yes |
| ControlGuideIndex | Index for control guide attributes | guideAttribute | controlKey | No |
| MappingReviews | Expert reviews of mappings | mappingKey | reviewKey | No |
| MappingFeedback | User feedback (thumbs up/down) | mappingKey | reviewerId | No |
| MappingJobs | Async mapping job tracking | job_id | - | No |
| Enrichment | Control enrichment cache | control_id | - | No |
| EmbeddingCache | ML embedding cache | control_id | model_version | No |

---

## Core Tables

### Frameworks

Stores compliance framework metadata including name, version, description, and status.

**Key Schema:**
- Partition Key: `frameworkName` (String)
- Sort Key: `version` (String)

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| FrameworkKeyIndex | frameworkKey | - | ALL |
| StatusIndex | status | frameworkName | ALL |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| frameworkName | String | Framework name (e.g., "NIST-SP-800-53") |
| version | String | Framework version (e.g., "R5") |
| frameworkKey | String | Composite key: `frameworkName#version` |
| displayName | String | Human-readable name |
| description | String | Framework description |
| status | String | ACTIVE, ARCHIVED, DRAFT |
| controlCount | Number | Total number of controls |
| source | String | Framework source/origin |
| sourceUrl | String | URL to official framework documentation |
| createdAt | String | ISO 8601 timestamp |
| updatedAt | String | ISO 8601 timestamp |
| createdBy | Map | Creator information |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "frameworkName": "NIST-SP-800-53",
  "version": "R5",
  "frameworkKey": "NIST-SP-800-53#R5",
  "displayName": "NIST SP 800-53 Revision 5",
  "description": "Security and Privacy Controls for Information Systems",
  "status": "ACTIVE",
  "controlCount": 1189,
  "source": "NIST",
  "sourceUrl": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z",
  "createdBy": {"system": "api"}
}
```

---

### FrameworkControls

Stores individual control definitions within a framework.

**Key Schema:**
- Partition Key: `frameworkKey` (String)
- Sort Key: `controlKey` (String)

**DynamoDB Streams:** Enabled (NEW_AND_OLD_IMAGES) - Used for trigger-based workflows when controls are created or modified.

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| ControlKeyIndex | controlKey | - | ALL |
| StatusIndex | status | controlKey | KEYS_ONLY |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| frameworkKey | String | Parent framework key: `frameworkName#version` |
| controlKey | String | Full control key: `frameworkKey#controlId` |
| controlId | String | Short control ID (e.g., "AC-1") |
| title | String | Control title |
| description | String | Full control description |
| controlGuide | String | Implementation guidance |
| family | String | Control family (e.g., "Access Control") |
| status | String | ACTIVE, ARCHIVED, DRAFT |
| parentControlId | String | Parent control for hierarchical controls |
| relatedControls | List | List of related control IDs |
| parameters | List | Control parameters |
| enhancements | List | Control enhancements |
| arn | String | ARN: `arn:aws:nexus:::control/{controlKey}` |
| createdAt | String | ISO 8601 timestamp |
| updatedAt | String | ISO 8601 timestamp |
| createdBy | Map | Creator information |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "frameworkKey": "NIST-SP-800-53#R5",
  "controlKey": "NIST-SP-800-53#R5#AC-1",
  "controlId": "AC-1",
  "title": "Policy and Procedures",
  "description": "Develop, document, and disseminate access control policy...",
  "controlGuide": "Organizations should establish access control policies that...",
  "family": "Access Control",
  "status": "ACTIVE",
  "parentControlId": null,
  "relatedControls": ["AC-2", "AC-3", "PL-1"],
  "arn": "arn:aws:nexus:::control/NIST-SP-800-53#R5#AC-1",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z",
  "createdBy": {"system": "api"}
}
```

---

### ControlMappings

Stores mappings between controls from different frameworks.

**Key Schema:**
- Partition Key: `controlKey` (String) - Source control key
- Sort Key: `mappedControlKey` (String) - Target control key

**DynamoDB Streams:** Enabled (NEW_AND_OLD_IMAGES) - Used for trigger-based workflows when mappings are created or updated.

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| MappingKeyIndex | mappingKey | - | ALL |
| StatusIndex | status | timestamp | ALL |
| WorkflowIndex | mappingWorkflowKey | timestamp | ALL |
| ControlStatusIndex | controlKey | status | ALL |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| controlKey | String | Source control key |
| mappedControlKey | String | Target control key |
| mappingKey | String | Unique mapping key (sorted concatenation) |
| mappingWorkflowKey | String | Workflow identifier for batch mappings |
| relationshipType | String | EQUIVALENT, PARTIAL, RELATED, NONE |
| confidence | Number | Confidence score (0.0-1.0) |
| similarityScore | Number | ML similarity score |
| rerankScore | Number | Cross-encoder rerank score |
| reasoning | String | LLM-generated mapping rationale |
| status | String | PENDING, APPROVED, REJECTED, ARCHIVED |
| timestamp | String | ISO 8601 timestamp |
| sourceEnrichment | Map | Enriched source control data |
| targetEnrichment | Map | Enriched target control data |
| arn | String | ARN: `arn:aws:nexus:::mapping/{mappingKey}` |
| createdAt | String | ISO 8601 timestamp |
| updatedAt | String | ISO 8601 timestamp |
| createdBy | Map | Creator information |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "controlKey": "AWS.ControlCatalog#1.0#IAM.21",
  "mappedControlKey": "NIST-SP-800-53#R5#AC-2",
  "mappingKey": "AWS.ControlCatalog#1.0#IAM.21|NIST-SP-800-53#R5#AC-2",
  "mappingWorkflowKey": "job_550e8400-e29b-41d4-a716-446655440000",
  "relationshipType": "PARTIAL",
  "confidence": 0.87,
  "similarityScore": 0.85,
  "rerankScore": 0.92,
  "reasoning": "Both controls address account management. AWS IAM.21 focuses on...",
  "status": "APPROVED",
  "timestamp": "2024-01-15T10:30:00Z",
  "arn": "arn:aws:nexus:::mapping/AWS.ControlCatalog#1.0#IAM.21|NIST-SP-800-53#R5#AC-2",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:35:00Z",
  "createdBy": {"system": "ml-pipeline"}
}
```

---

### ControlGuideIndex

Inverted index for searching controls by guide attributes (keywords, topics).

**Key Schema:**
- Partition Key: `guideAttribute` (String)
- Sort Key: `controlKey` (String)

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| ControlKeyIndex | controlKey | guideAttribute | KEYS_ONLY |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| guideAttribute | String | Keyword or topic from control guide |
| controlKey | String | Control key referencing FrameworkControls |
| weight | Number | Relevance weight for this attribute |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "guideAttribute": "multi-factor-authentication",
  "controlKey": "NIST-SP-800-53#R5#IA-2",
  "weight": 0.95
}
```

---

## Review & Feedback Tables

### MappingReviews

Stores expert reviews of control mappings.

**Key Schema:**
- Partition Key: `mappingKey` (String)
- Sort Key: `reviewKey` (String) - Format: `reviewerId#timestamp`

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| ReviewerIndex | reviewerId | submittedAt | ALL |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| mappingKey | String | Reference to ControlMappings |
| reviewKey | String | Composite: `reviewerId#timestamp` |
| reviewerId | String | Reviewer identifier |
| decision | String | APPROVE, REJECT, NEEDS_REVISION |
| comments | String | Review comments |
| suggestedRelationship | String | Reviewer's suggested relationship type |
| suggestedConfidence | Number | Reviewer's suggested confidence |
| submittedAt | String | ISO 8601 timestamp |
| updatedAt | String | ISO 8601 timestamp |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "mappingKey": "AWS.ControlCatalog#1.0#IAM.21|NIST-SP-800-53#R5#AC-2",
  "reviewKey": "expert-001#2024-01-15T14:30:00Z",
  "reviewerId": "expert-001",
  "decision": "APPROVE",
  "comments": "Mapping is accurate. Both controls address account lifecycle management.",
  "suggestedRelationship": "PARTIAL",
  "suggestedConfidence": 0.90,
  "submittedAt": "2024-01-15T14:30:00Z",
  "updatedAt": "2024-01-15T14:30:00Z"
}
```

---

### MappingFeedback

Stores user feedback (thumbs up/down) on mappings.

**Key Schema:**
- Partition Key: `mappingKey` (String)
- Sort Key: `reviewerId` (String)

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| UserFeedbackIndex | reviewerId | mappingKey | ALL |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| mappingKey | String | Reference to ControlMappings |
| reviewerId | String | User identifier |
| feedbackType | String | THUMBS_UP, THUMBS_DOWN |
| comment | String | Optional feedback comment |
| submittedAt | String | ISO 8601 timestamp |
| updatedAt | String | ISO 8601 timestamp |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "mappingKey": "AWS.ControlCatalog#1.0#IAM.21|NIST-SP-800-53#R5#AC-2",
  "reviewerId": "user-12345",
  "feedbackType": "THUMBS_UP",
  "comment": "This mapping helped me understand the relationship.",
  "submittedAt": "2024-01-15T16:00:00Z",
  "updatedAt": "2024-01-15T16:00:00Z"
}
```

---

## Async Processing Tables

### MappingJobs

Tracks async mapping workflow jobs started via POST /api/v1/mappings.

**Key Schema:**
- Partition Key: `job_id` (String)

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| StatusIndex | status | created_at | ALL |
| ControlKeyIndex | control_key | created_at | ALL |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| job_id | String | UUID job identifier |
| status | String | PENDING, RUNNING, COMPLETED, FAILED |
| control_key | String | Source control key being mapped |
| target_framework_key | String | Target framework key |
| target_control_ids | List | Optional specific target control IDs |
| execution_arn | String | Step Functions execution ARN |
| message_id | String | SQS message ID |
| mappings | List | Resulting mappings (when completed) |
| error | String | Error message (when failed) |
| created_at | String | ISO 8601 timestamp |
| updated_at | String | ISO 8601 timestamp |
| ttl | Number | TTL timestamp (7 days from creation) |

**Example Item:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5",
  "target_control_ids": null,
  "execution_arn": "arn:aws:states:us-east-1:123456789:execution:NexusMappingWorkflow:abc123",
  "message_id": "msg-12345",
  "mappings": [
    {
      "target_control_id": "SC-8",
      "similarity_score": 0.89,
      "rerank_score": 0.94,
      "reasoning": "Both controls address transmission confidentiality..."
    }
  ],
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:05:00Z",
  "ttl": 1705924800
}
```

---

## ML/Caching Tables

### Enrichment

Caches control enrichment results from the multi-agent enrichment system.

**Key Schema:**
- Partition Key: `control_id` (String) - Full control key

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Projection |
|------------|---------------|----------|------------|
| FrameworkIndex | framework_key | created_at | ALL |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| control_id | String | Full control key (same as controlKey) |
| framework_key | String | Parent framework key |
| enriched_interpretation | Map | Multi-agent enrichment result |
| intent | String | Control intent analysis |
| scope | String | Control scope analysis |
| implementation_guidance | String | Enhanced implementation guidance |
| keywords | List | Extracted keywords |
| related_concepts | List | Related security concepts |
| model_version | String | Enrichment model version |
| created_at | String | ISO 8601 timestamp |
| updated_at | String | ISO 8601 timestamp |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "control_id": "NIST-SP-800-53#R5#AC-2",
  "framework_key": "NIST-SP-800-53#R5",
  "enriched_interpretation": {
    "core_requirement": "Account lifecycle management",
    "security_objective": "Ensure authorized access only",
    "implementation_context": "IAM systems, directory services"
  },
  "intent": "Manage user accounts throughout their lifecycle",
  "scope": "All system accounts including privileged and service accounts",
  "implementation_guidance": "Implement automated account provisioning...",
  "keywords": ["account-management", "access-control", "identity"],
  "related_concepts": ["authentication", "authorization", "least-privilege"],
  "model_version": "enrichment-v2.1",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

---

### EmbeddingCache

Caches ML embeddings for controls to avoid recomputation.

**Key Schema:**
- Partition Key: `control_id` (String)
- Sort Key: `model_version` (String)

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| control_id | String | Full control key |
| model_version | String | Embedding model version (e.g., "qwen-8b-v1") |
| embedding | List | 4096-dimensional embedding vector |
| text_hash | String | Hash of input text (for cache invalidation) |
| created_at | String | ISO 8601 timestamp |
| expiryTime | Number | TTL timestamp (epoch seconds) |

**Example Item:**
```json
{
  "control_id": "NIST-SP-800-53#R5#AC-2",
  "model_version": "qwen-8b-v1",
  "embedding": [0.0234, -0.0156, 0.0089, ...],
  "text_hash": "sha256:abc123def456...",
  "created_at": "2024-01-15T10:00:00Z",
  "expiryTime": 1708430400
}
```

---

## Key Patterns

### Composite Keys

All composite keys use `#` as the delimiter:

- **frameworkKey**: `{frameworkName}#{version}` (e.g., `NIST-SP-800-53#R5`)
- **controlKey**: `{frameworkKey}#{controlId}` (e.g., `NIST-SP-800-53#R5#AC-1`)
- **mappingKey**: `{controlKey1}|{controlKey2}` (sorted, uses `|` delimiter)
- **reviewKey**: `{reviewerId}#{timestamp}`

### ARN Format

All resources use the triple-colon ARN format:
```
arn:aws:nexus:::resource/{key}
```

Examples:
- `arn:aws:nexus:::framework/NIST-SP-800-53#R5`
- `arn:aws:nexus:::control/NIST-SP-800-53#R5#AC-1`
- `arn:aws:nexus:::mapping/AWS.ControlCatalog#1.0#IAM.21|NIST-SP-800-53#R5#AC-2`

### TTL Configuration

All tables have TTL enabled on the `expiryTime` attribute (or `ttl` for MappingJobs). Default TTL periods:
- MappingJobs: 7 days
- Other tables: Configurable per item

---

## DynamoDB Streams

The following tables have DynamoDB Streams enabled with `NEW_AND_OLD_IMAGES` view type:

| Table | Stream Purpose |
|-------|----------------|
| FrameworkControls | Trigger enrichment workflows when controls are added/modified |
| ControlMappings | Trigger downstream processing when mappings change |

Streams are consumed by Lambda functions for event-driven workflows.

---

## CloudWatch Alarms

All tables have the following CloudWatch alarms configured:

**Sev2 Alarms (Critical):**
- ReadThrottledRequests
- WriteThrottledRequests
- SystemErrors (5xx)
- ReadLatency p99 > 100ms (Prod only)
- QueryLatency p99 > 200ms (Prod only)

**Sev3 Alarms (Warning):**
- UserErrors (4xx) > 10/5min
- ConditionalCheckFailedRequests > 50/5min

---

## Access Patterns

### Framework Operations
| Operation | Access Pattern |
|-----------|----------------|
| List all frameworks | Scan Frameworks (paginated) |
| List framework versions | Query Frameworks by frameworkName |
| Get specific framework | GetItem by frameworkName + version |
| Find framework by key | Query FrameworkKeyIndex |
| List active frameworks | Query StatusIndex where status=ACTIVE |

### Control Operations
| Operation | Access Pattern |
|-----------|----------------|
| List controls in framework | Query FrameworkControls by frameworkKey |
| Get specific control | GetItem by frameworkKey + controlKey |
| Find control by key | Query ControlKeyIndex |
| List active controls | Query StatusIndex where status=ACTIVE |

### Mapping Operations
| Operation | Access Pattern |
|-----------|----------------|
| List mappings for control | Query ControlMappings by controlKey |
| Get specific mapping | GetItem by controlKey + mappedControlKey |
| Find mapping by key | Query MappingKeyIndex |
| List mappings by status | Query StatusIndex |
| List mappings by workflow | Query WorkflowIndex |

### Job Operations
| Operation | Access Pattern |
|-----------|----------------|
| Get job status | GetItem by job_id |
| List jobs by status | Query StatusIndex |
| List jobs for control | Query ControlKeyIndex |

---

*Document generated: December 2024*
*Version: 2.0 - Includes MappingJobs, Enrichment, and EmbeddingCache tables*
