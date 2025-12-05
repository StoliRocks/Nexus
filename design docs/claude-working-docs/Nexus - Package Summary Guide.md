# Nexus Package Summary Guide

This document provides a comprehensive summary of all packages in the Nexus compliance control mapping pipeline.

---

## Table of Contents

1. [Overview](#overview)
2. [Package Categories](#package-categories)
3. [Shared Libraries](#shared-libraries)
4. [Agent Libraries](#agent-libraries)
5. [Lambda Handlers - CRUD Operations](#lambda-handlers---crud-operations)
6. [Lambda Handlers - Async Workflow](#lambda-handlers---async-workflow)
7. [Lambda Handlers - Step Functions Tasks](#lambda-handlers---step-functions-tasks)
8. [ECS Services](#ecs-services)
9. [Infrastructure](#infrastructure)
10. [Package Dependency Graph](#package-dependency-graph)
11. [Build and Deployment](#build-and-deployment)

---

## Overview

Nexus is an AWS compliance control mapping pipeline that maps AWS service controls to industry compliance frameworks (NIST, SOC2, PCI-DSS). The system comprises **22 packages** organized into distinct categories:

| Category | Count | Description |
|----------|-------|-------------|
| Shared Libraries | 2 | Foundational models and utilities |
| Agent Libraries | 2 | Multi-agent enrichment and reasoning |
| CRUD Lambda Handlers | 5 | API operations for resources |
| Async Workflow Lambda Handlers | 2 | Job creation and status |
| SQS Processing Lambda Handlers | 2 | Durable queue processing and DLQ redrive |
| Step Functions Task Lambda Handlers | 4 | Workflow task execution |
| Authorization Lambda | 1 | API Gateway authorizer |
| ECS Services | 2 | ML inference and agent execution |
| Infrastructure | 1 | CDK deployment |
| Placeholder | 1 | Reserved for future use |

---

## Package Categories

```
Nexus/
├── Shared Libraries
│   ├── NexusApplicationInterface/     # Pydantic models
│   └── NexusApplicationCommons/       # Shared utilities
│
├── Agent Libraries
│   ├── NexusEnrichmentAgent/          # Multi-agent enrichment
│   └── NexusReasoningAgent/           # Mapping rationale
│
├── Lambda Handlers - CRUD
│   ├── NexusFrameworkAPIHandlerLambda/
│   ├── NexusControlAPIHandlerLambda/
│   ├── NexusMappingAPIHandlerLambda/
│   ├── NexusMappingReviewAPIHandlerLambda/
│   └── NexusMappingFeedbackAPIHandlerLambda/
│
├── Lambda Handlers - Async Workflow
│   ├── NexusAsyncAPIHandlerLambda/
│   └── NexusStatusAPIHandlerLambda/
│
├── Lambda Handlers - SQS Processing
│   ├── NexusSqsTriggerLambda/          # SQS → Step Functions
│   └── NexusDlqRedriveLambda/          # DLQ message redrive
│
├── Lambda Handlers - Step Functions Tasks
│   ├── NexusScienceOrchestratorLambda/
│   ├── NexusEnrichmentAgentLambda/
│   ├── NexusReasoningAgentLambda/
│   └── NexusJobUpdaterLambda/
│
├── Authorization
│   └── NexusLambdaAuthorizer/
│
├── ECS Services
│   ├── NexusECSService/               # GPU ML inference
│   └── NexusStrandsAgentService/      # Agent execution
│
├── Infrastructure
│   └── NexusApplicationPipelineCDK/   # CDK stacks
│
└── Placeholder
    └── DefaultAPIEndpointHandlerLambda/
```

---

## Shared Libraries

### NexusApplicationInterface

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusApplicationInterface/` |
| **Purpose** | Pydantic data models and API contracts for all services |
| **Dependencies** | None (foundational package) |
| **External** | Pydantic, Python 3.11+ |

**Key Components:**

| Component | Path | Description |
|-----------|------|-------------|
| Control Model | `api/v1/models/control.py` | Control entity definition |
| Framework Model | `api/v1/models/framework.py` | Framework entity definition |
| Mapping Model | `api/v1/models/mapping.py` | Mapping entity with scores |
| Job Model | `api/v1/models/job.py` | Async job tracking |
| Review Model | `api/v1/models/mapping_review.py` | Expert review data |
| Feedback Model | `api/v1/models/feedback.py` | User feedback (thumbs up/down) |
| Enrichment Model | `api/v1/models/enrichment.py` | Enriched control data |
| Request Models | `api/v1/models/requests.py` | Pydantic request validators |
| Enums | `api/v1/models/enums.py` | Status and type enumerations |

**Usage:**
```python
from nexus_application_interface.api.v1 import (
    Control, Framework, Mapping, Job,
    ControlCreateRequest, BatchMappingsCreateRequest,
    MappingStatus, JobStatus
)
```

---

### NexusApplicationCommons

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusApplicationCommons/` |
| **Purpose** | Shared utilities for responses, DynamoDB, and LLM operations |
| **Dependencies** | NexusApplicationInterface, boto3 |
| **External** | boto3, Python 3.11+ |

**Key Components:**

| Component | Path | Description |
|-----------|------|-------------|
| Response Builder | `dynamodb/response_builder.py` | HTTP response formatters |
| Base Repository | `dynamodb/base_repository.py` | DynamoDB repository pattern |
| LLM Retry | `llm_utils/retry.py` | Retry logic for API calls |
| S3 Utils | `s3_utils/` | S3 streaming utilities |

**Response Builder Functions:**

| Function | Status Code | Use Case |
|----------|-------------|----------|
| `success_response(data)` | 200 | Successful GET/PUT |
| `created_response(data)` | 201 | Resource created |
| `accepted_response(data)` | 202 | Async job started |
| `not_found_response(resource, id)` | 404 | Resource not found |
| `validation_error_response(msg, field)` | 400 | Invalid request |
| `error_response(msg, status)` | Custom | General errors |

**Usage:**
```python
from nexus_application_commons.dynamodb.response_builder import (
    success_response, created_response, not_found_response,
    validation_error_response, error_response
)
```

---

## Agent Libraries

### NexusEnrichmentAgent

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusEnrichmentAgent/` |
| **Purpose** | Multi-agent enrichment system using strands framework |
| **Dependencies** | strands, boto3, AWS Bedrock |
| **External** | AWS Bedrock Claude models |

**Architecture:** 5 specialized agents + 1 master reviewer executing in parallel

**Key Components:**

| Component | Path | Description |
|-----------|------|-------------|
| Framework Profile Generator | `profiles/framework_profile_generator.py` | DynamicFrameworkProfileGenerator |
| AWS Control Profile Generator | `profiles/aws_control_profile_generator.py` | AWSControlProfileGenerator |
| Framework Processor | `processors/framework_processor.py` | ProfileDrivenMultiAgentProcessor |
| AWS Processor | `processors/aws_processor.py` | ProfileDrivenAWSProcessor |

**Agent Pipeline:**

| Agent | Responsibility |
|-------|----------------|
| Agent 1 | Objective classification |
| Agent 2 | Technical/Hybrid/Non-Technical filter |
| Agent 3 | Primary AWS services identification |
| Agent 4 | Security impact analysis |
| Agent 5 | Validation requirements |
| Master | Review and consolidation |

**Usage:**
```python
from nexus_enrichment_agent import (
    DynamicFrameworkProfileGenerator,
    ProfileDrivenMultiAgentProcessor
)

# Generate profile from sample controls
profiler = DynamicFrameworkProfileGenerator(framework_name="SOC-2")
profile = await profiler.generate_profile(sample_controls)

# Enrich controls with multi-agent system
processor = ProfileDrivenMultiAgentProcessor("SOC-2", profile)
result = processor.interpret_control_intent(metadata, control)
```

---

### NexusReasoningAgent

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusReasoningAgent/` |
| **Purpose** | Generates human-readable mapping rationale using Claude |
| **Dependencies** | boto3, AWS Bedrock |
| **External** | AWS Bedrock Claude models |

**Key Components:**

| Component | Path | Description |
|-----------|------|-------------|
| Reasoning Generator | `reasoning_generator.py` | ReasoningGenerator class |
| Prompts | `prompts.py` | Prompt templates |

**Capabilities:**

| Method | Description |
|--------|-------------|
| `generate_reasoning()` | Single mapping reasoning |
| `generate_batch_reasoning()` | Multiple mappings for same source |
| `generate_consolidated_reasoning()` | Efficient single API call |

**Usage:**
```python
from nexus_reasoning_agent import ReasoningGenerator, generate_reasoning

# Simple function call
reasoning = generate_reasoning(
    source_control_id="AWS-CONFIG-001",
    source_text="Ensures S3 buckets have versioning enabled",
    mapping={
        "target_control_id": "NIST-SC-28",
        "target_framework": "NIST-800-53",
        "text": "Protection of information at rest",
        "similarity_score": 0.85,
        "rerank_score": 0.92,
    }
)

# Batch processing
generator = ReasoningGenerator(model_id="anthropic.claude-3-haiku-20240307-v1:0")
results = generator.generate_batch_reasoning(source_id, source_text, mappings)
```

---

## Lambda Handlers - CRUD Operations

All CRUD Lambda handlers follow a consistent pattern:

```
handler.py (lambda_handler / api_endpoint_handler)
    ↓
service.py (XxxService class)
    ↓
DynamoDB operations via response_builder
```

### NexusFrameworkAPIHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusFrameworkAPIHandlerLambda/` |
| **Purpose** | Framework CRUD operations |
| **DynamoDB Table** | Frameworks |
| **Entry Point** | `api_endpoint_handler = lambda_handler` |

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/frameworks` | List all frameworks |
| GET | `/api/v1/frameworks/{name}` | List framework versions |
| GET | `/api/v1/frameworks/{name}/{version}` | Get specific framework |
| PUT | `/api/v1/frameworks/{name}/{version}` | Create/update framework |
| POST | `/api/v1/frameworks/{name}/{version}/archive` | Archive framework |

---

### NexusControlAPIHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusControlAPIHandlerLambda/` |
| **Purpose** | Control CRUD with batch operations (max 100) |
| **DynamoDB Table** | FrameworkControls |
| **Entry Point** | `api_endpoint_handler = lambda_handler` |

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/frameworks/{name}/{version}/controls` | List controls |
| GET | `/frameworks/{name}/{version}/controls/{id}` | Get control |
| PUT | `/frameworks/{name}/{version}/controls/{id}` | Create/update control |
| POST | `/frameworks/{name}/{version}/batchControls` | Batch create (max 100) |
| PUT | `/frameworks/{name}/{version}/controls/{id}/archive` | Archive control |
| POST | `/frameworks/{name}/{version}/controls/batchArchive` | Batch archive |

---

### NexusMappingAPIHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusMappingAPIHandlerLambda/` |
| **Purpose** | Mapping CRUD with batch operations |
| **DynamoDB Table** | ControlMappings |
| **Entry Point** | `api_endpoint_handler = lambda_handler` |

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mappings` | List mappings |
| GET | `/api/v1/mappings/{mappingId}` | Get mapping |
| GET | `/api/v1/controls/{controlId}/mappings` | Get mappings for control |
| POST | `/api/v1/batchMappings` | Batch create (max 100) |
| PUT | `/api/v1/mappings/{mappingId}/archive` | Archive mapping |

**Key Features:**
- Deterministic composite keys (sorted `controlKey1|controlKey2`)
- ML scores: `similarity_score` (Qwen), `rerank_score` (ModernBERT)

---

### NexusMappingReviewAPIHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusMappingReviewAPIHandlerLambda/` |
| **Purpose** | Expert review operations for QA workflow |
| **DynamoDB Table** | MappingReviews |
| **Entry Point** | `api_endpoint_handler = lambda_handler` |

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mappings/{mappingId}/reviews` | List reviews |
| POST | `/api/v1/mappings/{mappingId}/reviews` | Create review |
| PUT | `/api/v1/mappings/{mappingId}/reviews/{reviewId}` | Update review |

**Key Features:**
- Tracks whether mapping is correct (Boolean)
- Mark as final review flag
- Optional feedback/comments

---

### NexusMappingFeedbackAPIHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusMappingFeedbackAPIHandlerLambda/` |
| **Purpose** | User thumbs-up/thumbs-down feedback collection |
| **DynamoDB Table** | MappingFeedbacks |
| **Entry Point** | `api_endpoint_handler = lambda_handler` |

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mappings/{mappingId}/feedbacks` | List feedback |
| POST | `/api/v1/mappings/{mappingId}/feedbacks` | Create feedback |
| PUT | `/api/v1/mappings/{mappingId}/feedbacks/{feedbackId}` | Update feedback |

**Key Constraint:** One feedback per user per mapping (enforced by unique key)

---

## Lambda Handlers - Async Workflow

### NexusAsyncAPIHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusAsyncAPIHandlerLambda/` |
| **Purpose** | Async mapping job creation (starts Step Functions) |
| **DynamoDB Tables** | Jobs, Frameworks, FrameworkControls |
| **Entry Point** | `api_endpoint_handler = lambda_handler` |

**Endpoint:** POST `/api/v1/mappings`

**Request:**
```json
{
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5",
  "target_control_ids": ["AC-1", "AC-2"]
}
```

**Response (202 Accepted):**
```json
{
  "mappingId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACCEPTED",
  "statusUrl": "/api/v1/mappings/{mappingId}",
  "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetFrameworkKey": "NIST-SP-800-53#R5"
}
```

**Key Functions:**

| Function | Description |
|----------|-------------|
| `create_job()` | Creates PENDING job record (7-day TTL) |
| `start_workflow()` | Starts Step Functions execution |
| `validate_control_key_format()` | Validates composite key format |
| `validate_framework_key_format()` | Validates framework key format |
| `control_exists()` | Checks ControlKeyIndex GSI |
| `framework_exists()` | Queries Frameworks table |

---

### NexusStatusAPIHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusStatusAPIHandlerLambda/` |
| **Purpose** | Job status queries |
| **DynamoDB Table** | Jobs |
| **Entry Point** | `api_endpoint_handler = lambda_handler` |

**Endpoint:** GET `/api/v1/mappings/{mappingId}`

**Job Status Flow:**
```
PENDING → RUNNING → COMPLETED / FAILED
```

**Response includes:**
- Control key, framework key
- Creation/update timestamps
- Results (if COMPLETED)
- Error message (if FAILED)

---

## Lambda Handlers - SQS Processing

These Lambda handlers provide durable message processing for the async mapping workflow.

### NexusSqsTriggerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusSqsTriggerLambda/` |
| **Purpose** | Consume SQS messages and start Step Functions workflows |
| **DynamoDB Table** | MappingJobs |
| **SQS Queue** | MappingRequestQueue |
| **Entry Point** | `lambda_handler` |

**Trigger:** SQS event source mapping (batch size: 10)

**Process:**
1. Receives batch of SQS messages from MappingRequestQueue
2. For each message, starts Step Functions workflow
3. Updates job status from PENDING to RUNNING
4. Returns partial batch failure report for failed messages

**Message Format:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5",
  "target_control_ids": ["AC-1", "AC-2"]
}
```

**Key Functions:**

| Function | Description |
|----------|-------------|
| `process_message()` | Parse message, start workflow, update job |
| `start_workflow()` | Start Step Functions execution |
| `update_job_status()` | Transition job from PENDING to RUNNING |

**Environment Variables:**

| Variable | Description |
|----------|-------------|
| `JOB_TABLE_NAME` | MappingJobs DynamoDB table |
| `STATE_MACHINE_ARN` | Step Functions state machine ARN |

**Failure Handling:**
- Failed messages reported via `batchItemFailures` response
- SQS automatically retries failed messages (3 attempts)
- After max retries, messages move to Dead Letter Queue

---

### NexusDlqRedriveLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusDlqRedriveLambda/` |
| **Purpose** | Redrive failed messages from DLQ after bug fixes |
| **SQS Queues** | MappingRequestDLQ (source), MappingRequestQueue (target) |
| **Entry Point** | `lambda_handler` |

**Trigger:** Manual invocation or CloudWatch Events schedule

**Request (Optional Parameters):**
```json
{
  "dry_run": false,
  "max_messages": 100
}
```

**Response:**
```json
{
  "statusCode": 200,
  "body": {
    "messages_processed": 50,
    "messages_redriven": 48,
    "messages_failed": 2,
    "dry_run": false
  }
}
```

**Key Functions:**

| Function | Description |
|----------|-------------|
| `receive_dlq_messages()` | Poll messages from DLQ |
| `redrive_message()` | Send message to main queue |
| `delete_message()` | Remove from DLQ after successful redrive |

**Environment Variables:**

| Variable | Description |
|----------|-------------|
| `DLQ_URL` | MappingRequestDLQ URL |
| `MAIN_QUEUE_URL` | MappingRequestQueue URL |

**Use Case:**
- After deploying bug fix, trigger this Lambda to reprocess failed requests
- Use `dry_run: true` to preview which messages would be redriven
- Use `max_messages` to limit batch size for controlled reprocessing

---

## Lambda Handlers - Step Functions Tasks

### NexusScienceOrchestratorLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusScienceOrchestratorLambda/` |
| **Purpose** | ML pipeline orchestration (embed → retrieve → rerank) |
| **DynamoDB Tables** | Controls, Frameworks, Enrichment, EmbeddingCache |
| **External** | NexusECSService HTTP endpoint |
| **Entry Point** | `lambda_handler` |

**Actions:**

| Action | Description |
|--------|-------------|
| `validate_control` | Verify source control exists |
| `check_enrichment` | Check for cached enriched text |
| `map_control` | Execute full ML pipeline |

**ML Pipeline Steps:**

1. Call `/embed` - Generate 4096-dim Qwen embedding
2. Call `/retrieve` - Cosine similarity search
3. Call `/rerank` - ModernBERT cross-encoder scoring
4. Return top-k candidates with scores

---

### NexusEnrichmentAgentLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusEnrichmentAgentLambda/` |
| **Purpose** | Control enrichment via multi-agent system |
| **DynamoDB Table** | Enrichment |
| **External** | NexusStrandsAgentService `/enrich` endpoint |
| **Entry Point** | `lambda_handler` |

**Process:**
1. Receives control data from Step Functions
2. Calls NexusStrandsAgentService `/enrich`
3. Stores enriched text in DynamoDB
4. Returns enrichment result

---

### NexusReasoningAgentLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusReasoningAgentLambda/` |
| **Purpose** | Generate mapping reasoning (Map state task) |
| **External** | NexusStrandsAgentService `/reason` endpoint |
| **Entry Point** | `lambda_handler` |

**Execution:** Runs in Map state with max 5 concurrent executions

**Process:**
1. Receives mapping data from Map state iterator
2. Calls NexusStrandsAgentService `/reason`
3. Returns human-readable rationale

---

### NexusJobUpdaterLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusJobUpdaterLambda/` |
| **Purpose** | Update job with results or errors |
| **DynamoDB Table** | Jobs |
| **Entry Point** | `lambda_handler` |

**Key Operations:**

| Function | Description |
|----------|-------------|
| `update_job_completed()` | Writes mappings + reasoning to job |
| `update_job_failed()` | Writes error message to job |

---

## Lambda Handlers - Authorization

### NexusLambdaAuthorizer

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusLambdaAuthorizer/` |
| **Purpose** | API Gateway custom authorizer with dual auth |
| **External** | AWS Midway, BRASS Bindle Lock |
| **Entry Point** | `lambda_handler` |

**Authentication Methods:**

| Method | Description |
|--------|-------------|
| Midway Tokens | Human users - validates via AWS Midway |
| IAM Principals | Services - validates ARN format |

**Features:**
- BRASS Bindle Lock integration for persona assignment (SA/QA)
- Fail-closed security (any auth error → Deny policy)
- Returns IAM policy + auth context

---

## ECS Services

### NexusECSService

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusECSService/` |
| **Purpose** | GPU-accelerated ML inference |
| **Infrastructure** | ECS on g5.12xlarge (4x NVIDIA A10G GPUs) |
| **Technology** | FastAPI + PyTorch + Transformers |

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/embed` | Generate 4096-dim Qwen embedding |
| POST | `/api/v1/retrieve` | Cosine similarity search |
| POST | `/api/v1/rerank` | ModernBERT cross-encoder scoring |
| GET | `/health` | Health check (immediate 200) |
| GET | `/ready` | Readiness check (200 when loaded) |

**ML Models:**

| Model | Purpose | Output |
|-------|---------|--------|
| Qwen-embedding-8B | Bi-encoder embeddings | 4096-dim vectors |
| ModernBERT | Cross-encoder reranking | Relevance scores |

**Performance:**

| Operation | Latency |
|-----------|---------|
| Embed (cache miss) | 50-100ms |
| Embed (cache hit) | <10ms |
| Retrieve (1K targets) | <50ms |
| Retrieve (10K targets) | <200ms |
| Rerank (50 candidates) | 2-3 seconds |

**Architecture:**

| Component | Path | Description |
|-----------|------|-------------|
| Interfaces | `interfaces/` | BaseRetriever, BaseReranker contracts |
| Retrievers | `algorithms/retrievers/` | Qwen implementation |
| Rerankers | `algorithms/rerankers/` | ModernBERT implementation |
| API | `app/routers/` | FastAPI endpoints |
| Services | `app/services/` | Business logic |

---

### NexusStrandsAgentService

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusStrandsAgentService/` |
| **Purpose** | FastAPI wrapper for agent execution |
| **Infrastructure** | ECS container |
| **Technology** | FastAPI + strands + AWS Bedrock |

**Endpoints - Enrichment:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/enrich` | Enrich single control |
| POST | `/api/v1/enrich/batch` | Batch enrich (max 10) |
| POST | `/api/v1/profile/generate` | Generate framework profile |

**Endpoints - Reasoning:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reason` | Single mapping reasoning |
| POST | `/api/v1/reason/batch` | Batch reasoning (max 20) |
| POST | `/api/v1/reason/consolidated` | Consolidated (max 10) |

**Endpoints - Health:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| GET | `/` | Service info |
| GET | `/docs` | OpenAPI documentation |

**Configuration:**

| Variable | Default |
|----------|---------|
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| `REASONING_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` |

**Dependencies:**
- NexusEnrichmentAgent (multi-agent enrichment)
- NexusReasoningAgent (mapping rationale)

---

## Infrastructure

### NexusApplicationPipelineCDK

| Attribute | Value |
|-----------|-------|
| **Location** | `NexusApplicationPipelineCDK/` |
| **Purpose** | TypeScript AWS CDK infrastructure-as-code |
| **Technology** | AWS CDK v2 + TypeScript |

**Capabilities:**
- API Gateway with Lambda handlers
- Step Functions state machine orchestration
- DynamoDB tables and GSI definitions
- ECS services deployment
- Lambda function configurations
- Custom authorizer setup
- Cross-stage deployment pipeline

**Build Commands:**
```bash
npm install
npm run build
npm run test
npx cdk synth
npx cdk list
npx cdk deploy
```

**Deployment Stages:**

| Stage | Account | Description |
|-------|---------|-------------|
| Beta | 909139952351 | Development |
| Gamma | 098092129359 | Pre-production |
| Prod | 305345571965 | Production |

---

## Placeholder Package

### DefaultAPIEndpointHandlerLambda

| Attribute | Value |
|-----------|-------|
| **Location** | `DefaultAPIEndpointHandlerLambda/` |
| **Status** | Empty placeholder (no source code) |
| **Purpose** | Reserved for future use |

---

## Package Dependency Graph

```
                    ┌─────────────────────────────────┐
                    │   NexusApplicationInterface     │
                    │       (foundational)            │
                    └─────────────┬───────────────────┘
                                  │
                    ┌─────────────▼───────────────────┐
                    │   NexusApplicationCommons       │
                    │     (depends on Interface)      │
                    └─────────────┬───────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ CRUD Lambda   │       │ NexusEnrichment │       │ NexusReasoning  │
│ Handlers (5)  │       │     Agent       │       │     Agent       │
└───────────────┘       └────────┬────────┘       └────────┬────────┘
                                 │                         │
                                 └────────────┬────────────┘
                                              │
                           ┌──────────────────▼──────────────────┐
                           │      NexusStrandsAgentService       │
                           │  (depends on Enrichment + Reasoning)│
                           └──────────────────┬──────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
        ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
        │ Enrichment Lambda │     │  Reasoning Lambda │     │ Async Handler     │
        │ (Step Function)   │     │  (Step Function)  │     │ (publishes SQS)   │
        └───────────────────┘     └───────────────────┘     └─────────┬─────────┘
                    │                         │                       │
                    └─────────────────────────┼───────────────────────┘
                                              │
                           ┌──────────────────▼──────────────────┐
                           │      MappingRequestQueue (SQS)      │
                           │         (durability layer)          │
                           └──────────────────┬──────────────────┘
                                              │
                           ┌──────────────────▼──────────────────┐
                           │       NexusSqsTriggerLambda         │
                           │    (consumes SQS, starts workflow)  │
                           └──────────────────┬──────────────────┘
                                              │
                           ┌──────────────────▼──────────────────┐
                           │     NexusScienceOrchestrator        │
                           │   (calls NexusECSService APIs)      │
                           └──────────────────┬──────────────────┘
                                              │
                           ┌──────────────────▼──────────────────┐
                           │         NexusECSService             │
                           │    (independent ML infrastructure)  │
                           └──────────────────┬──────────────────┘
                                              │
                           ┌──────────────────▼──────────────────┐
                           │    NexusApplicationPipelineCDK      │
                           │   (orchestrates all deployments)    │
                           └─────────────────────────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │            SQS Failure Path                 │
                    │                                             │
                    │  MappingRequestQueue (3 retries)            │
                    │           │                                 │
                    │           ▼                                 │
                    │  MappingRequestDLQ (failed messages)        │
                    │           │                                 │
                    │           ▼                                 │
                    │  NexusDlqRedriveLambda (manual redrive)     │
                    │           │                                 │
                    │           ▼                                 │
                    │  MappingRequestQueue (reprocessed)          │
                    └─────────────────────────────────────────────┘
```

---

## Build and Deployment

### Python Packages (Brazil Build)

```bash
# Build
brazil-build

# Test
brazil-build test
brazil-build test --addopts="-k test_pattern"

# Code Quality
brazil-build format        # black + isort
brazil-build check-format  # Verify formatting
brazil-build mypy          # Type checking
brazil-build lint          # flake8 linting

# Run Python
brazil-runtime-exec python script.py
```

### CDK Infrastructure (TypeScript)

```bash
cd NexusApplicationPipelineCDK

npm install
npm run build
npm run test
npx cdk synth
npx cdk deploy
```

### Code Style

| Setting | Value |
|---------|-------|
| Line length | 100 characters |
| Formatter | black + isort (profile=black) |
| Type hints | Required (mypy enabled) |
| Linting | flake8 |

### Testing

| Framework | Use Case |
|-----------|----------|
| pytest | Python unit tests |
| moto | AWS service mocking |
| jest | CDK TypeScript tests |
| aws_cdk.assertions | CDK stack assertions |

---

## Key Design Patterns

### Database Key Formats

| Key Type | Format | Example |
|----------|--------|---------|
| Framework Key | `{name}#{version}` | `NIST-SP-800-53#R5` |
| Control Key | `{frameworkKey}#{controlId}` | `NIST-SP-800-53#R5#AC-1` |
| Mapping Key | `sorted({key1}, {key2})` | `AWS.EC2#1.0#PR.1\|NIST-SP-800-53#R5#AC-1` |

### ARN Format

```
arn:aws:nexus:::resource/{key}
```

### Lambda Handler Pattern

```python
# handler.py
def lambda_handler(event: dict, context: Any) -> dict:
    service = XxxService()
    return service.some_method(...)

api_endpoint_handler = lambda_handler  # BATS alias

# service.py
class XxxService:
    def __init__(
        self,
        dynamodb_resource: Optional[Any] = None,
        table_name: Optional[str] = None,
    ):
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name or TABLE_NAME)
```

### Step Functions Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SQS Durability Layer                                  │
│                                                                             │
│  API Gateway → AsyncHandler → SQS Queue → SqsTriggerLambda                  │
│                  (PENDING)      (durable)    (RUNNING)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Step Functions Workflow                               │
│                                                                             │
│  Start → ValidateControl → CheckEnrichment → [RunEnrichment] →              │
│  ScienceOrchestrator → Map(Reasoning) → JobUpdater → End                    │
│                                                                             │
│  OnError → JobUpdater(FAILED)                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Generated for the Nexus Compliance Mapping Pipeline*
