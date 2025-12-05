# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nexus is an AWS compliance control mapping pipeline that maps AWS service controls to industry frameworks (NIST, SOC2, PCI-DSS). It uses GPU-accelerated ML models (Qwen-embedding-8B, ModernBERT reranker) and Claude LLM agents for semantic retrieval and reasoning.

## Monorepo Structure

- **NexusMappingPipelineRepo/** - Legacy package (moved to /home/stvwhite/projects/NexusMappingPipelineRepo)
- **NexusApplicationInterface/** - Pydantic models and data contracts for API/state machine
- **NexusApplicationCommons/** - Shared utilities (response_builder, llm_utils, s3_utils, dynamodb)
- **NexusEnrichmentAgent/** - Multi-agent enrichment system using strands
- **NexusReasoningAgent/** - Reasoning generator for mapping rationale
- **NexusApplicationPipelineCDK/** - TypeScript CDK infrastructure (API Gateway, Lambda handlers, DynamoDB)
- **NexusECSService/** - GPU ML inference service (Qwen embeddings, ModernBERT reranker)
- **NexusStrandsAgentService/** - ECS service for strands-based agent execution (enrichment + reasoning)
- **NexusFrameworkAPIHandlerLambda/** - Framework CRUD operations
- **NexusControlAPIHandlerLambda/** - Control CRUD operations
- **NexusMappingAPIHandlerLambda/** - Mapping CRUD operations
- **NexusMappingReviewAPIHandlerLambda/** - Review operations for mappings
- **NexusMappingFeedbackAPIHandlerLambda/** - Feedback (thumbs up/down) operations
- **NexusLambdaAuthorizer/** - API Gateway custom authorizer
- **NexusAsyncAPIHandlerLambda/** - Async job creation (POST /mappings - starts Step Functions)
- **NexusStatusAPIHandlerLambda/** - Job status queries (GET /mappings/{mappingId})
- **NexusScienceOrchestratorLambda/** - ML pipeline orchestration (embed → retrieve → rerank)
- **NexusEnrichmentAgentLambda/** - Control enrichment Step Functions task
- **NexusReasoningAgentLambda/** - Mapping reasoning Step Functions task
- **NexusJobUpdaterLambda/** - Job status updates after workflow completion
- **NexusSqsTriggerLambda/** - SQS trigger that starts Step Functions from queue messages
- **NexusDlqRedriveLambda/** - DLQ redrive utility for retry after bug fixes
- **DefaultAPIEndpointHandlerLambda/** - Default/fallback API endpoint handler

## Refactoring Status

Breaking NexusMappingPipelineRepo into smaller libraries for CI/CD optimization.

### Completed
- [x] **NexusApplicationInterface/api/v1/models/** - Added Pydantic DAOs (Control, Framework, Mapping, Job, Feedback, etc.)
- [x] **NexusApplicationInterface/api/v1/models/requests.py** - Added Pydantic request models for API input validation
- [x] **NexusApplicationCommons/dynamodb/** - Added BaseRepository and API response builders
- [x] **NexusEnrichmentAgent/** - Multi-agent enrichment system (profiles + processors)
- [x] **NexusReasoningAgent/** - Reasoning generator for mapping rationale
- [x] **NexusControlAPIHandlerLambda/** - Control CRUD with batch operations
- [x] **NexusFrameworkAPIHandlerLambda/** - Framework CRUD operations
- [x] **NexusMappingAPIHandlerLambda/** - Mapping CRUD with batch operations
- [x] **NexusMappingReviewAPIHandlerLambda/** - Review operations
- [x] **NexusMappingFeedbackAPIHandlerLambda/** - Feedback operations
- [x] **NexusApplicationPipelineCDK** - Updated to use individual Lambda handlers
- [x] **NexusECSService** - GPU ML inference service (Qwen embeddings, ModernBERT reranker)
- [x] **NexusStrandsAgentService** - ECS container for strands-based agent execution (enrichment + reasoning)
- [x] **Add README files to Lambda packages** - Documented all Lambda handler packages with usage examples
- [x] **Lambda handler DAO refactoring** - All handlers parse request bodies into Pydantic DAOs for type safety and validation
- [x] **NexusAsyncAPIHandlerLambda** - Async handler (POST /mappings - starts Step Functions workflow)
- [x] **NexusStatusAPIHandlerLambda** - Status handler (GET /mappings/{id} - job status)
- [x] **NexusScienceOrchestratorLambda** - Science orchestrator (ML pipeline: embed → retrieve → rerank)
- [x] **NexusEnrichmentAgentLambda** - Enrichment agent (calls NexusStrandsAgentService /enrich)
- [x] **NexusReasoningAgentLambda** - Reasoning agent (calls NexusStrandsAgentService /reason)
- [x] **NexusJobUpdaterLambda** - Job updater (updates job status after workflow completion)
- [x] **NexusSqsTriggerLambda** - SQS trigger Lambda (consumes queue, starts Step Functions)
- [x] **NexusDlqRedriveLambda** - DLQ redrive Lambda (retry failed requests after fixes)
- [x] **SQS Infrastructure** - MappingRequestQueue, MappingRequestDLQ, CloudWatch alarms

### Pending
- [ ] **Align all Config files** - Review and standardize build system configuration across all packages (pending guidance on brazilpython vs no-op)

### Architecture Diagram
```
Nexus/
├── NexusApplicationInterface/      # Shared Pydantic models
│   └── api/v1/models/              # Control, Framework, Mapping, Job, Feedback
├── NexusApplicationCommons/        # Shared utilities
│   └── dynamodb/                   # BaseRepository, response builders
├── NexusEnrichmentAgent/           # Multi-agent enrichment (strands)
│   ├── profiles/                   # Framework & AWS profile generators
│   └── processors/                 # Multi-agent processors
├── NexusReasoningAgent/            # Reasoning generator (strands)
├── NexusApplicationPipelineCDK/    # TypeScript CDK stacks
│   └── lib/stacks/apihandlers/     # Handler configurations
├── NexusFrameworkAPIHandlerLambda/ # Framework CRUD
├── NexusControlAPIHandlerLambda/   # Control CRUD
├── NexusMappingAPIHandlerLambda/   # Mapping CRUD
├── NexusMappingReviewAPIHandlerLambda/   # Review operations
├── NexusMappingFeedbackAPIHandlerLambda/ # Feedback operations
├── NexusLambdaAuthorizer/          # API Gateway authorizer
├── NexusECSService/                # GPU ML service - Qwen/ModernBERT (complete)
├── NexusStrandsAgentService/       # ECS container for strands agents (complete)
│   └── app/routers/                # /enrich, /reason endpoints
├── NexusAsyncAPIHandlerLambda/     # Async job creation (complete)
├── NexusStatusAPIHandlerLambda/    # Job status queries (complete)
├── NexusScienceOrchestratorLambda/ # ML pipeline orchestration (complete)
├── NexusEnrichmentAgentLambda/     # Enrichment Step Function task (complete)
├── NexusReasoningAgentLambda/      # Reasoning Step Function task (complete)
├── NexusJobUpdaterLambda/          # Job status updates (complete)
├── NexusSqsTriggerLambda/          # SQS trigger for Step Functions (complete)
├── NexusDlqRedriveLambda/          # DLQ redrive utility (complete)
├── DefaultAPIEndpointHandlerLambda/ # Default/fallback API handler
├── design docs/                    # Architecture and design documentation
└── claude-working-docs/            # Claude working markdown files

# Legacy package moved out of monorepo:
# /home/stvwhite/projects/NexusMappingPipelineRepo/
```

## API Endpoints

### Frameworks (`/api/v1/frameworks`)
| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| GET | `/frameworks` | NexusFrameworkAPIHandlerLambda | List all frameworks |
| GET | `/frameworks/{name}` | NexusFrameworkAPIHandlerLambda | List framework versions |
| GET | `/frameworks/{name}/{version}` | NexusFrameworkAPIHandlerLambda | Get specific framework |
| PUT | `/frameworks/{name}/{version}` | NexusFrameworkAPIHandlerLambda | Create/update framework |
| POST | `/frameworks/{name}/{version}/archive` | NexusFrameworkAPIHandlerLambda | Archive framework |

### Controls (`/api/v1/frameworks/{name}/{version}/controls`)
| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| GET | `/controls` | NexusControlAPIHandlerLambda | List controls |
| GET | `/controls/{controlId}` | NexusControlAPIHandlerLambda | Get control |
| PUT | `/controls/{controlId}` | NexusControlAPIHandlerLambda | Create/update control |
| POST | `/batchControls` | NexusControlAPIHandlerLambda | Batch create (max 100) |
| POST | `/controls/batchArchive` | NexusControlAPIHandlerLambda | Batch archive |
| PUT | `/controls/{controlId}/archive` | NexusControlAPIHandlerLambda | Archive control |

### Mappings (`/api/v1/mappings`)
| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| GET | `/mappings` | NexusMappingAPIHandlerLambda | List mappings |
| GET | `/mappings/{mappingId}` | NexusMappingAPIHandlerLambda | Get mapping |
| PUT | `/mappings/{mappingId}` | NexusMappingAPIHandlerLambda | Update mapping |
| POST | `/batchMappings` | NexusMappingAPIHandlerLambda | Batch create (max 100) |
| PUT | `/mappings/{mappingId}/archive` | NexusMappingAPIHandlerLambda | Archive mapping |

### Reviews (`/api/v1/mappings/{mappingId}/reviews`)
| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| GET | `/reviews` | NexusMappingReviewAPIHandlerLambda | List reviews |
| POST | `/reviews` | NexusMappingReviewAPIHandlerLambda | Create review |
| PUT | `/reviews/{reviewId}` | NexusMappingReviewAPIHandlerLambda | Update review |

### Feedbacks (`/api/v1/mappings/{mappingId}/feedbacks`)
| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| GET | `/feedbacks` | NexusMappingFeedbackAPIHandlerLambda | List feedbacks |
| POST | `/feedbacks` | NexusMappingFeedbackAPIHandlerLambda | Create feedback |
| PUT | `/feedbacks/{feedbackId}` | NexusMappingFeedbackAPIHandlerLambda | Update feedback |

### ECS ML Service (`/api/v1` on NexusECSService)
| Method | Endpoint | Service | Description |
|--------|----------|---------|-------------|
| POST | `/embed` | NexusECSService | Generate 4096-dim Qwen embedding |
| POST | `/retrieve` | NexusECSService | Cosine similarity search |
| POST | `/rerank` | NexusECSService | Cross-encoder ModernBERT reranking |
| GET | `/health` | NexusECSService | Health check (always 200 during startup) |
| GET | `/ready` | NexusECSService | Readiness check (200 when models loaded) |

### Strands Agent Service (`/api/v1` on NexusStrandsAgentService)
| Method | Endpoint | Service | Description |
|--------|----------|---------|-------------|
| POST | `/enrich` | NexusStrandsAgentService | Enrich single control via multi-agent system |
| POST | `/enrich/batch` | NexusStrandsAgentService | Batch enrich controls (max 10) |
| POST | `/profile/generate` | NexusStrandsAgentService | Generate framework profile from samples |
| POST | `/reason` | NexusStrandsAgentService | Generate reasoning for single mapping |
| POST | `/reason/batch` | NexusStrandsAgentService | Batch reasoning (max 20) |
| POST | `/reason/consolidated` | NexusStrandsAgentService | Consolidated reasoning (single API call) |
| GET | `/health` | NexusStrandsAgentService | Health check |
| GET | `/ready` | NexusStrandsAgentService | Readiness check (verifies agent packages) |

## Build Commands (Brazil)

```bash
# Build
brazil-build

# Test
brazil-build test
brazil-build test --addopts="-k test_pattern"           # Run specific tests
brazil-build test --addopts="test/test_lambdas/test_async_handler.py"  # Single file

# Code quality
brazil-build format        # black + isort
brazil-build check-format  # Verify formatting
brazil-build mypy          # Type checking
brazil-build lint          # flake8

# CDK (TypeScript)
cd NexusApplicationPipelineCDK
npm install
npm run build
npm run test
npx cdk synth

# Run Python
brazil-runtime-exec python script.py
```

## Architecture

```
API Gateway -> AsyncAPIHandler -> MappingRequestQueue -> SQS Trigger Lambda -> Step Functions
                    |                    |                                          |
                    v                    v (on failure)                             +-> ECS GPU Service
              MappingJobs          MappingRequestDLQ                                +-> enrichment_agent (Claude)
                (PENDING)               |                                           +-> reasoning_agent (Claude)
                                        v (after fix)                               +-> job_updater
                                  DLQ Redrive Lambda
                                        |
                                        v
                                  MappingRequestQueue
```

**SQS-based durability:** Requests are queued before Step Functions execution. If processing fails
due to bugs requiring code fixes, requests are preserved in DLQ and can be retried after deployment.

**Lambda pattern:** Each Lambda follows `handler.py` (entry) + `service.py` (logic) structure.

**Response format:** All handlers use response builders from NexusApplicationCommons:
- `success_response(data)` - 200 OK
- `created_response(data)` - 201 Created
- `accepted_response(data)` - 202 Accepted
- `not_found_response(resource, id)` - 404 Not Found
- `validation_error_response(message, field=None)` - 400 Bad Request
- `error_response(message, status_code)` - Custom error

## Key Patterns

**Database keys:**
- `frameworkKey`: `frameworkName#version` (e.g., `NIST-SP-800-53#R5`)
- `controlKey`: `frameworkKey#controlId` (e.g., `NIST-SP-800-53#R5#AC-1`)
- `mappingKey`: `controlKey1|controlKey2` (sorted concatenation)

**ARN format:** `arn:aws:nexus:::resource/{key}` (triple colon)

**Creator format:** `{"system": "api"}` for API-created resources

**Using shared models:**
```python
from nexus_application_interface.api.v1 import Control, Framework, Mapping, Job
from nexus_application_commons.dynamodb.response_builder import (
    success_response,
    created_response,
    not_found_response,
    validation_error_response,
)
```

**Using request models for input validation:**
```python
from pydantic import ValidationError
from nexus_application_interface.api.v1 import (
    FrameworkCreateRequest,
    ControlCreateRequest,
    BatchControlsCreateRequest,
    BatchArchiveRequest,
    BatchMappingsCreateRequest,
    ReviewCreateRequest,
    ReviewUpdateRequest,
    FeedbackCreateRequest,
    FeedbackUpdateRequest,
)

# Parse and validate request body
try:
    body = json.loads(event.get("body", "{}"))
    request = ControlCreateRequest.model_validate(body)
    # Access typed fields: request.title, request.description, request.control_guide
except ValidationError as e:
    return validation_error_response(e.errors()[0]["msg"])
```

**Lambda handler pattern:**
```python
# handler.py
from nexus_<name>_api_handler_lambda.service import SomeService
from nexus_application_commons.dynamodb.response_builder import (
    error_response,
    validation_error_response,
)

def lambda_handler(event: dict, context: Any) -> dict:
    service = SomeService()
    # Route based on method and path
    if http_method == "GET":
        return service.get_item(item_id)
    # ...

# Alias for BATS Lambda configuration
api_endpoint_handler = lambda_handler
```

**Service class pattern:**
```python
# service.py
from typing import Any, Dict, Optional

class SomeService:
    def __init__(
        self,
        dynamodb_resource: Optional[Any] = None,
        table_name: Optional[str] = None,
    ):
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or TABLE_NAME
        self.table = self.dynamodb.Table(self.table_name)

    def get_item(self, item_id: str) -> Dict[str, Any]:
        response = self.table.get_item(Key={"id": item_id})
        item = response.get("Item")
        if not item:
            return not_found_response("Item", item_id)
        return success_response(item)
```

**Note:** Always use explicit `Optional[T]` when a parameter has `None` as default value.
mypy with `no_implicit_optional=True` (default in Python 3.10+) will reject `param: str = None`.

**Using NexusEnrichmentAgent:**
```python
from nexus_enrichment_agent import (
    DynamicFrameworkProfileGenerator,
    ProfileDrivenMultiAgentProcessor,
)

# Generate profile from sample controls
profiler = DynamicFrameworkProfileGenerator(framework_name="SOC-2")
profile = await profiler.generate_profile(sample_controls)

# Process controls with profile-enhanced agents
processor = ProfileDrivenMultiAgentProcessor("SOC-2", profile)
result = processor.interpret_control_intent(metadata, control)
```

**Using NexusReasoningAgent:**
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

# Or use class for batch processing
generator = ReasoningGenerator(model_id="anthropic.claude-3-haiku-20240307-v1:0")
results = generator.generate_batch_reasoning(source_id, source_text, mappings)
```

**Using NexusECSService (HTTP API):**
```python
import httpx

# Generate embedding
response = httpx.post("http://ecs-service:8000/api/v1/embed", json={
    "control_id": "IAM.21",
    "text": "Ensure IAM users are managed through centralized identity provider"
})
# Returns: {"control_id": "IAM.21", "embedding": [...4096 floats...], "cache_hit": false}

# Similarity retrieval
response = httpx.post("http://ecs-service:8000/api/v1/retrieve", json={
    "source_embedding": [...],  # 4096-dim normalized vector
    "target_embeddings": [[...], [...], ...],  # List of embeddings
    "top_k": 50
})
# Returns: {"candidates": [{"control_id": "0", "similarity": 0.95}, ...]}

# Rerank candidates
response = httpx.post("http://ecs-service:8000/api/v1/rerank", json={
    "source_text": "Ensure users authenticate with MFA",
    "candidates": [
        {"control_id": "CTRL-001", "text": "Enable MFA for accounts"},
        {"control_id": "CTRL-002", "text": "Rotate access keys"}
    ]
})
# Returns: {"rankings": [{"control_id": "CTRL-001", "score": 0.92}, ...]}
```

**Using NexusStrandsAgentService (HTTP API):**
```python
import httpx

# Enrich a control via multi-agent system
response = httpx.post("http://strands-service:8000/api/v1/enrich", json={
    "metadata": {
        "frameworkName": "NIST-SP-800-53",
        "frameworkVersion": "R5"
    },
    "control": {
        "shortId": "AC-1",
        "title": "Access Control Policy",
        "description": "The organization develops, documents, and disseminates..."
    }
})
# Returns: {"controlId": "AC-1", "enrichedInterpretation": {...}, "status": "success"}

# Generate framework profile for enhanced enrichment
response = httpx.post("http://strands-service:8000/api/v1/profile/generate", json={
    "frameworkName": "SOC-2",
    "sampleControls": [
        {"shortId": "CC1.1", "title": "Control Environment", "description": "..."},
        {"shortId": "CC1.2", "title": "Board Oversight", "description": "..."}
    ]
})
# Returns: {"frameworkName": "SOC-2", "profile": {...}, "status": "success"}

# Generate mapping reasoning
response = httpx.post("http://strands-service:8000/api/v1/reason", json={
    "sourceControlId": "AWS-IAM-001",
    "sourceText": "Ensure IAM policies are attached only to groups or roles",
    "mapping": {
        "targetControlId": "NIST-AC-1",
        "targetFramework": "NIST-SP-800-53",
        "text": "Access control policy and procedures",
        "similarityScore": 0.85,
        "rerankScore": 0.92
    }
})
# Returns: {"sourceControlId": "...", "targetControlId": "...", "reasoning": "...", "status": "success"}
```

## Code Style

- Line length: 100 characters
- Formatter: black + isort (profile=black)
- Type hints required (mypy enabled)
- Linting: flake8
- `known_first_party` imports: stacks, shared, lambdas, ecs_service, nexus_enrichment_agent

## Testing

- Framework: pytest with moto for AWS mocking
- CDK testing uses `aws_cdk.assertions.Template` (TypeScript: jest)
- Coverage reports: `build/brazil-documentation/coverage/`

**Test fixture pattern:**
```python
@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="TableName",
            KeySchema=[...],
            AttributeDefinitions=[...],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb

@pytest.fixture
def service(dynamodb_table):
    return SomeService(dynamodb_resource=dynamodb_table, table_name="TableName")
```

## Deployment Environments

| Stage | Account | Description |
|-------|---------|-------------|
| Beta | 909139952351 | Development |
| Gamma | 098092129359 | Pre-production |
| Prod | 305345571965 | Production |

## GPU Server (Reference)

The original enrichment agent code was ported from a remote GPU server:
- Host: `ubuntu@174.129.80.239`
- SSH Key: `/home/stvwhite/.ssh/finetuned-model-ssh.pem`
- Code location: `/home/ubuntu/workplace/NexusGraphAgentApp/NexusEngine/src/nexus_engine/agents/enrichment_sim_v2/`
- Now available as `NexusEnrichmentAgent` package

## Step Functions Lambda Reference

All Step Functions Lambdas have been migrated from NexusMappingPipelineRepo to individual packages.

### NexusAsyncAPIHandlerLambda
**Package:** `NexusAsyncAPIHandlerLambda/`
**Endpoint:** POST `/api/v1/mappings` (starts async mapping workflow via SQS)

**Request Format:**
```json
{
  "control_key": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "target_framework_key": "NIST-SP-800-53#R5",
  "target_control_ids": ["AC-1", "AC-2"]  // Optional
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
- `create_job()` - Creates job record using Job DAO (PENDING status, 7-day TTL)
- `enqueue_mapping_request()` - Publishes to MappingRequestQueue for durable processing
- `start_workflow()` - Alias for enqueue_mapping_request (backward compatibility)
- `validate_control_key_format()` - Pattern: `^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+#.+$`
- `validate_framework_key_format()` - Pattern: `^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+$`
- `control_exists()` - Queries ControlKeyIndex GSI, returns suggestions if not found
- `framework_exists()` - Queries Frameworks table, returns available frameworks if not found

**Environment Variables:**
- `JOB_TABLE_NAME` - Jobs DynamoDB table (default: "MappingJobs")
- `MAPPING_REQUEST_QUEUE_URL` - SQS queue URL for durable processing
- `FRAMEWORKS_TABLE_NAME` - Frameworks table (default: "Frameworks")
- `CONTROLS_TABLE_NAME` - Controls table (default: "FrameworkControls")

**Dependencies:**
- `NexusApplicationInterface` - Job model, JobStatus enum
- `NexusApplicationCommons` - BaseRepository pattern

### NexusSqsTriggerLambda
**Package:** `NexusSqsTriggerLambda/`
**Trigger:** SQS event source from MappingRequestQueue

Consumes mapping requests from SQS and starts Step Functions workflows. Provides durability -
if Step Functions fails due to bugs requiring code fixes, requests are preserved in DLQ.

**Key Functions:**
- `start_workflow()` - Starts Step Functions execution for each SQS message
- `JobRepository.update_status()` - Updates job status to IN_PROGRESS

**Environment Variables:**
- `STATE_MACHINE_ARN` - Step Functions state machine ARN
- `JOB_TABLE_NAME` - Jobs DynamoDB table (default: "MappingJobs")

**SQS Configuration:**
- Batch size: 1 (process one message at a time)
- Partial batch failure reporting enabled
- Max receive count: 3 (then moves to DLQ)

### NexusDlqRedriveLambda
**Package:** `NexusDlqRedriveLambda/`
**Invocation:** Manual or scheduled

Redrives failed messages from MappingRequestDLQ back to MappingRequestQueue after bug fixes.

**Request Format:**
```json
{
  "dry_run": true,        // Optional: just count messages
  "max_messages": 50      // Optional: limit messages to redrive
}
```

**Response:**
```json
{
  "statusCode": 200,
  "messages_redriven": 25,
  "dlq_message_count_before": 30,
  "message": "Successfully redriven 25 messages"
}
```

**Environment Variables:**
- `DLQ_URL` - MappingRequestDLQ URL
- `MAIN_QUEUE_URL` - MappingRequestQueue URL

### NexusStatusAPIHandlerLambda
**Package:** `NexusStatusAPIHandlerLambda/`
**Endpoint:** GET `/api/v1/mappings/{mappingId}`

Returns job status and results (if completed). Job statuses: PENDING → RUNNING → COMPLETED/FAILED

### NexusScienceOrchestratorLambda
**Package:** `NexusScienceOrchestratorLambda/`

Step Functions task that orchestrates ML pipeline:
1. Calls NexusECSService `/embed` for source control embedding
2. Calls NexusECSService `/retrieve` for cosine similarity candidates
3. Calls NexusECSService `/rerank` for cross-encoder reranking
4. Returns top-k mapping candidates

### NexusEnrichmentAgentLambda
**Package:** `NexusEnrichmentAgentLambda/`

Step Functions task that invokes NexusStrandsAgentService `/enrich` endpoint to enrich control text using multi-agent system.

### NexusReasoningAgentLambda
**Package:** `NexusReasoningAgentLambda/`

Step Functions task that invokes NexusStrandsAgentService `/reason` endpoint.
Runs in Map state with max 5 concurrent executions to generate reasoning for each mapping.

### NexusJobUpdaterLambda
**Package:** `NexusJobUpdaterLambda/`

Final Step Functions task that updates job status:
- `update_job_completed()` - Sets status=COMPLETED, merges mappings with reasoning
- `update_job_failed()` - Sets status=FAILED, stores error message

**Step Functions Workflow:**
```
Start → ValidateControl → CheckEnrichment → [RunEnrichment] → ScienceModel → Map(Reasoning) → JobUpdater → End
                                                                    ↓
                                                              OnError → JobUpdater(FAILED)
```

## SQS Infrastructure

### MappingRequestQueue
**Type:** Standard SQS Queue
**Purpose:** Durable buffer for async mapping requests

| Property | Value |
|----------|-------|
| Visibility Timeout | 60 seconds |
| Message Retention | 7 days |
| Max Receive Count | 3 (then DLQ) |
| Encryption | AWS managed |

### MappingRequestDLQ
**Type:** Standard SQS Queue (Dead Letter Queue)
**Purpose:** Stores failed messages for retry after bug fixes

| Property | Value |
|----------|-------|
| Message Retention | 14 days |
| Encryption | AWS managed |

### CloudWatch Alarms
- **DLQ Not Empty:** Triggers when messages appear in DLQ (indicates failures)
- **Queue Backlog:** Triggers when ApproximateNumberOfMessagesVisible > 100
- **Message Age:** Triggers when ApproximateAgeOfOldestMessage > 1 hour

## Document Generation Best Practices

When creating documentation that needs to be in DOCX format, use Pandoc with the following best practices:

### Basic Conversion Command
```bash
pandoc input.md \
  --from=markdown+pipe_tables+backtick_code_blocks+fenced_code_attributes \
  --to=docx \
  --highlight-style=kate \
  --standalone \
  --wrap=none \
  --toc \
  --toc-depth=3 \
  -o output.docx
```

### Recommended Options

| Option | Purpose |
|--------|---------|
| `--from=markdown+pipe_tables+backtick_code_blocks+fenced_code_attributes` | Enable better table and code block support |
| `--highlight-style=kate` | Syntax highlighting for code blocks (alternatives: `pygments`, `monochrome`, `tango`) |
| `--standalone` | Generate complete document with metadata |
| `--wrap=none` | Prevent unwanted line wrapping in output |
| `--toc` | Auto-generate table of contents |
| `--toc-depth=3` | Include headings up to level 3 in TOC |
| `--reference-doc=template.docx` | Apply custom corporate styling (optional) |

### Creating a Custom Reference Template
```bash
# Generate default reference document
pandoc -o custom-reference.docx --print-default-data-file reference.docx

# Edit custom-reference.docx in Word to customize styles, then use:
pandoc input.md --reference-doc=custom-reference.docx -o output.docx
```

### Available Highlight Styles
View all available styles: `pandoc --list-highlight-styles`
- `pygments` (default)
- `kate` (recommended for technical docs)
- `monochrome` (print-friendly)
- `tango`, `espresso`, `zenburn`, `breezeDark`

### Markdown Best Practices for DOCX Conversion

**Tables:** Use pipe tables with alignment colons
```markdown
| Column 1 | Column 2 | Column 3 |
|:---------|:--------:|---------:|
| Left     | Center   | Right    |
```

**Code blocks:** Use fenced code blocks with language specifier
```markdown
```python
def example():
    return "Hello"
```
```

**Document metadata:** Use YAML front matter
```yaml
---
title: "Document Title"
author: "Compliance Engineering Team"
date: "December 2024"
---
```

### Design Docs Location
All design documentation is stored in: `design docs/`

**Distribution Files (docx):**
- `Nexus - High Level Design Doc (Revision 4).docx` - HLD reference
- `Nexus - Database Schema.docx` - Database schema reference
- `Nexus - Package Architecture and Pipeline Guide.docx` - Package architecture (generated)
- `Nexus - Mapping API Architecture.docx` - Mapping API flow through all packages (generated)
- `Nexus - Package Summary Guide.docx` - Comprehensive summary of all 22 packages (generated)
- `Nexus - Enrichment Agent Migration Analysis.docx` - Comparison of GPU server enrichment_sim_v2 vs NexusEnrichmentAgent package (generated)

**Markdown Source Files:** `design docs/claude-working-docs/`
- `Nexus - Package Architecture and Pipeline Guide.md`
- `Nexus-Mapping-API-Architecture.md`
- `Nexus - Package Summary Guide.md`
- `Nexus - Enrichment Agent Migration Analysis.md`
