# Nexus - Package Architecture and Pipeline Guide

## Document Information
- **Version:** 1.0
- **Last Updated:** December 2024
- **Author:** Compliance Engineering Team

---

## 1. Executive Summary

Nexus is an AWS compliance control mapping system that automatically maps AWS service controls to industry compliance frameworks (NIST SP 800-53, SOC2, PCI-DSS, HIPAA, ISO 27001, etc.). The system uses a combination of GPU-accelerated machine learning models for semantic similarity matching and Claude LLM agents for intelligent enrichment and reasoning.

### Key Capabilities
- Semantic embedding generation using Qwen-embedding-8B (4096 dimensions)
- Cross-encoder reranking using ModernBERT for precision
- Multi-agent control enrichment using Claude
- Automated reasoning generation for compliance mappings
- RESTful API for framework, control, and mapping management

### Quick Reference: Package Summary

| Package | Type | Purpose |
|---------|------|---------|
| **NexusApplicationInterface** | Shared Library | Pydantic models and data contracts for API requests/responses |
| **NexusApplicationCommons** | Shared Library | Response builders, DynamoDB helpers, S3 utilities |
| **NexusEnrichmentAgent** | Shared Library | Multi-agent control enrichment using strands framework |
| **NexusReasoningAgent** | Shared Library | Reasoning generator for mapping rationale |
| **NexusFrameworkAPIHandlerLambda** | API Lambda | Framework CRUD operations (`/frameworks/*`) |
| **NexusControlAPIHandlerLambda** | API Lambda | Control CRUD and batch operations (`/controls/*`) |
| **NexusMappingAPIHandlerLambda** | API Lambda | Mapping CRUD and batch operations (`/mappings/*`) |
| **NexusMappingReviewAPIHandlerLambda** | API Lambda | QA review operations (`/mappings/{id}/reviews/*`) |
| **NexusMappingFeedbackAPIHandlerLambda** | API Lambda | Feedback operations (`/mappings/{id}/feedbacks/*`) |
| **NexusLambdaAuthorizer** | API Lambda | API Gateway custom authorizer for authentication |
| **NexusAsyncAPIHandlerLambda** | Step Functions | Creates job, starts async mapping workflow |
| **NexusStatusAPIHandlerLambda** | Step Functions | Returns job status and results |
| **NexusScienceOrchestratorLambda** | Step Functions | ML pipeline: embed → retrieve → rerank |
| **NexusEnrichmentAgentLambda** | Step Functions | Control enrichment via NexusStrandsAgentService |
| **NexusReasoningAgentLambda** | Step Functions | Reasoning generation via NexusStrandsAgentService |
| **NexusJobUpdaterLambda** | Step Functions | Updates job status to COMPLETED or FAILED |
| **NexusECSService** | ECS Service | GPU ML inference (Qwen embeddings, ModernBERT reranker) |
| **NexusStrandsAgentService** | ECS Service | Claude agents for enrichment and reasoning |
| **NexusApplicationPipelineCDK** | Infrastructure | TypeScript CDK (API Gateway, Lambda, DynamoDB, Step Functions) |
| **NexusMappingPipelineRepo** | Infrastructure | Legacy package being decomposed |

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway                                     │
│                         (NexusLambdaAuthorizer)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  Framework    │         │   Control     │         │   Mapping     │
│  API Lambda   │         │  API Lambda   │         │  API Lambda   │
└───────────────┘         └───────────────┘         └───────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
                          ┌───────────────┐
                          │   DynamoDB    │
                          │    Tables     │
                          └───────────────┘
```

### 2.2 Async Mapping Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────────────┐
│ POST        │     │ Async API   │     │         Step Functions              │
│ /mappings   │────▶│   Lambda    │────▶│                                     │
└─────────────┘     └─────────────┘     │  ┌─────────────────────────────┐   │
                                        │  │ 1. ValidateControl          │   │
┌─────────────┐                         │  │ 2. CheckEnrichment          │   │
│ GET         │     ┌─────────────┐     │  │ 3. [RunEnrichment]          │   │
│ /mappings/  │────▶│ Status API  │     │  │ 4. ScienceOrchestrator      │   │
│ {id}        │     │   Lambda    │     │  │ 5. Map(ReasoningAgent)      │   │
└─────────────┘     └─────────────┘     │  │ 6. JobUpdater               │   │
                                        │  └─────────────────────────────┘   │
                                        └─────────────────────────────────────┘
                                                        │
                    ┌───────────────────────────────────┼───────────────────┐
                    │                                   │                   │
                    ▼                                   ▼                   ▼
          ┌─────────────────┐              ┌─────────────────┐   ┌─────────────────┐
          │ NexusECSService │              │ NexusStrands    │   │    DynamoDB     │
          │ (GPU ML Models) │              │ AgentService    │   │     Tables      │
          │                 │              │ (Claude Agents) │   │                 │
          │ • Qwen Embed    │              │                 │   │ • Jobs          │
          │ • ModernBERT    │              │ • Enrichment    │   │ • Mappings      │
          │   Reranker      │              │ • Reasoning     │   │ • Controls      │
          └─────────────────┘              └─────────────────┘   └─────────────────┘
```

---

## 3. Package Inventory

### 3.1 Shared Libraries

| Package | Description | Dependencies |
|---------|-------------|--------------|
| **NexusApplicationInterface** | Pydantic models and data contracts for API requests/responses and state machine data | pydantic |
| **NexusApplicationCommons** | Shared utilities: response builders, DynamoDB helpers, S3 utils | boto3, NexusApplicationInterface |
| **NexusEnrichmentAgent** | Multi-agent enrichment system using strands framework | boto3, strands-agents |
| **NexusReasoningAgent** | Reasoning generator for mapping rationale using Claude | boto3 |

### 3.2 API Handler Lambdas

| Package | Endpoint | Description |
|---------|----------|-------------|
| **NexusFrameworkAPIHandlerLambda** | `/api/v1/frameworks/*` | CRUD operations for compliance frameworks |
| **NexusControlAPIHandlerLambda** | `/api/v1/frameworks/{name}/{version}/controls/*` | CRUD and batch operations for framework controls |
| **NexusMappingAPIHandlerLambda** | `/api/v1/mappings/*` | CRUD and batch operations for control mappings |
| **NexusMappingReviewAPIHandlerLambda** | `/api/v1/mappings/{id}/reviews/*` | Review operations for mappings |
| **NexusMappingFeedbackAPIHandlerLambda** | `/api/v1/mappings/{id}/feedbacks/*` | Feedback (thumbs up/down) operations |
| **NexusLambdaAuthorizer** | API Gateway | Custom authorizer for API authentication |

### 3.3 Step Functions Lambdas

| Package | Step | Description |
|---------|------|-------------|
| **NexusAsyncAPIHandlerLambda** | Entry Point | Creates job, starts Step Functions workflow |
| **NexusStatusAPIHandlerLambda** | Query | Returns job status and results |
| **NexusScienceOrchestratorLambda** | ML Pipeline | Orchestrates embed → retrieve → rerank |
| **NexusEnrichmentAgentLambda** | Enrichment | Calls NexusStrandsAgentService /enrich |
| **NexusReasoningAgentLambda** | Reasoning | Calls NexusStrandsAgentService /reason |
| **NexusJobUpdaterLambda** | Completion | Updates job status to COMPLETED or FAILED |

### 3.4 ECS Services

| Package | Description | Endpoints |
|---------|-------------|-----------|
| **NexusECSService** | GPU ML inference service with Qwen embeddings and ModernBERT reranker | `/embed`, `/retrieve`, `/rerank`, `/health`, `/ready` |
| **NexusStrandsAgentService** | Strands-based agent service for enrichment and reasoning | `/enrich`, `/reason`, `/profile/generate`, `/health`, `/ready` |

### 3.5 Infrastructure

| Package | Description |
|---------|-------------|
| **NexusApplicationPipelineCDK** | TypeScript CDK infrastructure (API Gateway, Lambda handlers, DynamoDB, Step Functions) |
| **NexusMappingPipelineRepo** | Legacy package being decomposed |

---

## 4. Data Flow

### 4.1 Async Mapping Request Flow

1. **Client Request**
   - POST `/api/v1/mappings` with `control_key` and `target_framework_key`

2. **NexusAsyncAPIHandlerLambda**
   - Validates control_key format (`frameworkName#version#controlId`)
   - Validates framework_key format (`frameworkName#version`)
   - Verifies control exists in Controls table
   - Verifies target framework exists in Frameworks table
   - Creates job record in Jobs table (status: PENDING)
   - Starts Step Functions execution
   - Returns 202 Accepted with `mappingId`

3. **Step Functions Workflow**

   a. **ValidateControl** (NexusScienceOrchestratorLambda)
      - Verifies source control exists
      - Returns control data

   b. **CheckEnrichment** (NexusScienceOrchestratorLambda)
      - Checks if enrichment exists for control
      - If not, triggers enrichment step

   c. **RunEnrichment** (NexusEnrichmentAgentLambda) - Optional
      - Calls NexusStrandsAgentService `/enrich`
      - Stores enriched text in Enrichment table

   d. **ScienceOrchestrator** (NexusScienceOrchestratorLambda)
      - Calls NexusECSService `/embed` for source control
      - Gets/creates embeddings for target controls
      - Calls NexusECSService `/retrieve` for top-k candidates
      - Calls NexusECSService `/rerank` for final ranking
      - Returns ranked mapping candidates

   e. **Map(ReasoningAgent)** (NexusReasoningAgentLambda)
      - Runs in parallel (max 5 concurrent)
      - Calls NexusStrandsAgentService `/reason` for each mapping
      - Returns reasoning text for each mapping

   f. **JobUpdater** (NexusJobUpdaterLambda)
      - Merges mappings with reasoning
      - Updates job status to COMPLETED
      - Stores final mappings in Jobs table

4. **Status Query**
   - GET `/api/v1/mappings/{mappingId}`
   - Returns job status (PENDING, RUNNING, COMPLETED, FAILED)
   - For COMPLETED jobs, returns mappings with reasoning

---

## 5. Key Patterns

### 5.1 Database Key Patterns

| Key Type | Format | Example |
|----------|--------|---------|
| `frameworkKey` | `frameworkName#version` | `NIST-SP-800-53#R5` |
| `controlKey` | `frameworkKey#controlId` | `NIST-SP-800-53#R5#AC-1` |
| `mappingKey` | `controlKey1\|controlKey2` | `AWS.ControlCatalog#1.0#IAM.1\|NIST-SP-800-53#R5#AC-1` |

### 5.2 Lambda Handler Pattern

Each Lambda follows a consistent structure:

```
Package/
├── src/nexus_<name>_lambda/
│   ├── __init__.py
│   ├── handler.py      # Entry point, routing
│   └── service.py      # Business logic
└── test/
    ├── conftest.py     # Shared fixtures
    └── nexus_<name>_lambda/
        └── test_handler.py
```

**handler.py:**
- Receives event from API Gateway or Step Functions
- Instantiates service class
- Routes to appropriate service method
- Handles exceptions

**service.py:**
- Contains business logic
- Accepts DynamoDB resource in constructor (for testing)
- Returns response dicts using NexusApplicationCommons builders

### 5.3 Response Builders

All API responses use builders from `NexusApplicationCommons`:

```python
from nexus_application_commons.dynamodb.response_builder import (
    success_response,      # 200 OK
    created_response,      # 201 Created
    accepted_response,     # 202 Accepted
    not_found_response,    # 404 Not Found
    validation_error_response,  # 400 Bad Request
    error_response,        # Custom error
)
```

### 5.4 Service Dependency Injection

Services accept optional DynamoDB resource for testability:

```python
class SomeService:
    def __init__(self, dynamodb_resource=None, table_name: str = None):
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table_name = table_name or os.environ.get("TABLE_NAME")
        self.table = self.dynamodb.Table(self.table_name)
```

---

## 6. ML Pipeline Details

### 6.1 Embedding Generation (NexusECSService)

- **Model:** Qwen-embedding-8B
- **Output:** 4096-dimensional normalized vectors
- **Caching:** Embeddings cached in EmbeddingCache DynamoDB table
- **Endpoint:** POST `/api/v1/embed`

### 6.2 Similarity Retrieval (NexusECSService)

- **Method:** Cosine similarity between source and target embeddings
- **Output:** Top-k candidates with similarity scores
- **Endpoint:** POST `/api/v1/retrieve`

### 6.3 Reranking (NexusECSService)

- **Model:** ModernBERT cross-encoder
- **Purpose:** Precision improvement over embedding similarity
- **Output:** Reranked candidates with rerank scores
- **Threshold:** Default 0.5 minimum score
- **Endpoint:** POST `/api/v1/rerank`

### 6.4 Control Enrichment (NexusStrandsAgentService)

- **Model:** Claude via AWS Bedrock
- **Purpose:** Expand control text with compliance context
- **Multi-Agent System:** Uses strands framework for orchestration
- **Endpoint:** POST `/api/v1/enrich`

### 6.5 Reasoning Generation (NexusStrandsAgentService)

- **Model:** Claude via AWS Bedrock
- **Purpose:** Generate human-readable rationale for mappings
- **Output:** 2-3 sentence explanation of mapping relationship
- **Endpoint:** POST `/api/v1/reason`

---

## 7. DynamoDB Tables

| Table | Primary Key | Sort Key | Purpose |
|-------|-------------|----------|---------|
| Frameworks | frameworkName | version | Framework metadata |
| Controls | frameworkKey | controlKey | Control definitions |
| Mappings | mappingKey | - | Control-to-control mappings |
| Jobs | job_id | - | Async mapping job status |
| Enrichment | control_id | - | Cached enriched control text |
| EmbeddingCache | control_id | model_version | Cached embeddings |
| Reviews | mappingId | reviewId | Mapping reviews |
| Feedbacks | mappingId | feedbackId | Mapping feedback |

---

## 8. Environment Variables

### 8.1 Common Variables

| Variable | Description |
|----------|-------------|
| `AWS_DEFAULT_REGION` | AWS region (us-east-1) |
| `CONTROLS_TABLE_NAME` | Controls DynamoDB table |
| `FRAMEWORKS_TABLE_NAME` | Frameworks DynamoDB table |

### 8.2 Step Functions Lambdas

| Variable | Lambda | Description |
|----------|--------|-------------|
| `JOB_TABLE_NAME` | Async, Status, JobUpdater | Jobs table |
| `STATE_MACHINE_ARN` | Async | Step Functions ARN |
| `SCIENCE_API_ENDPOINT` | ScienceOrchestrator | NexusECSService URL |
| `STRANDS_SERVICE_ENDPOINT` | Enrichment, Reasoning | NexusStrandsAgentService URL |
| `ENRICHMENT_TABLE_NAME` | ScienceOrchestrator, Enrichment | Enrichment cache table |
| `EMBEDDING_CACHE_TABLE_NAME` | ScienceOrchestrator | Embedding cache table |

---

## 9. Deployment

### 9.1 Environments

| Stage | AWS Account | Purpose |
|-------|-------------|---------|
| Beta | 909139952351 | Development |
| Gamma | 098092129359 | Pre-production |
| Prod | 305345571965 | Production |

### 9.2 CDK Deployment

```bash
cd NexusApplicationPipelineCDK
npm install
npm run build
npx cdk synth
npx cdk deploy --all
```

---

## 10. Testing

### 10.1 Unit Tests

Each package includes unit tests using pytest and moto for AWS mocking:

```bash
brazil-build test
brazil-build test --addopts="-k test_pattern"
```

### 10.2 Test Fixture Pattern

```python
@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(...)
        table.wait_until_exists()
        yield dynamodb

@pytest.fixture
def service(dynamodb_table):
    return SomeService(dynamodb_resource=dynamodb_table, table_name="TestTable")
```

---

## 11. API Reference Summary

### 11.1 Framework Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/frameworks` | List all frameworks |
| GET | `/frameworks/{name}` | List versions |
| GET | `/frameworks/{name}/{version}` | Get framework |
| PUT | `/frameworks/{name}/{version}` | Create/update |
| POST | `/frameworks/{name}/{version}/archive` | Archive |

### 11.2 Control Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/controls` | List controls |
| GET | `/controls/{id}` | Get control |
| PUT | `/controls/{id}` | Create/update |
| POST | `/batchControls` | Batch create |
| POST | `/controls/batchArchive` | Batch archive |

### 11.3 Mapping Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mappings` | Start async mapping |
| GET | `/mappings/{id}` | Get status/results |
| PUT | `/mappings/{id}` | Update mapping |
| POST | `/batchMappings` | Batch create |

---

## 12. HLD Alignment Analysis

This section compares the current implementation against the High Level Design Doc (Revision 4) and Database Schema documents, explaining alignments and intentional deviations.

### 12.1 Architecture Alignment

| HLD Component | Implementation | Status | Notes |
|---------------|----------------|--------|-------|
| API Gateway with Authorizer | NexusLambdaAuthorizer | ✅ Aligned | Custom authorizer for RBAC |
| Framework CRUD APIs | NexusFrameworkAPIHandlerLambda | ✅ Aligned | All endpoints implemented |
| Control CRUD APIs | NexusControlAPIHandlerLambda | ✅ Aligned | Includes batch operations |
| Mapping APIs | NexusMappingAPIHandlerLambda | ✅ Aligned | CRUD and batch operations |
| Review APIs | NexusMappingReviewAPIHandlerLambda | ✅ Aligned | QA workflow support |
| Feedback APIs | NexusMappingFeedbackAPIHandlerLambda | ✅ Aligned | Thumbs up/down feedback |
| Async mapping workflow | Step Functions + Lambdas | ✅ Aligned | Uses Step Functions as designed |

### 12.2 Database Schema Alignment

| HLD Table | Implementation | Status | Notes |
|-----------|----------------|--------|-------|
| Frameworks | Frameworks table | ✅ Aligned | PK: frameworkName, SK: version |
| FrameworkControls | Controls table | ✅ Aligned | PK: frameworkKey, SK: controlKey |
| ControlMappings | Mappings table | ⚠️ Simplified | See deviation notes below |
| MappingReviews | Reviews table | ✅ Aligned | PK: mappingId, SK: reviewId |
| MappingFeedback | Feedbacks table | ✅ Aligned | PK: mappingId, SK: feedbackId |
| ControlGuideIndex | Not implemented | ⏸️ Deferred | P1 feature for CG attribute indexing |

### 12.3 Intentional Deviations

#### 12.3.1 Mapping Pipeline Architecture

**HLD Design:**
```
NewControlTrigger → SQS → MapControlFanout → SQS → MapControlBatchProcessor → Model
```

**Current Implementation:**
```
POST /mappings → AsyncAPIHandler → Step Functions → ScienceOrchestrator → ECS ML Service
```

**Rationale:** The HLD describes an event-driven architecture with DynamoDB Streams triggering Lambda functions through SQS queues. The implementation uses a request-driven approach with Step Functions for several reasons:

1. **Simpler orchestration** - Step Functions provides built-in state management, retries, and error handling
2. **Better visibility** - Step Functions console shows workflow execution status
3. **Easier debugging** - Each step's input/output is captured for troubleshooting
4. **On-demand mapping** - Current use case is request-driven rather than event-driven

**Future consideration:** If automatic mapping on control INSERT is required, DynamoDB Streams can trigger the existing Step Functions workflow.

#### 12.3.2 Science Model Invocation

**HLD Design:** Direct Lambda invocation of fine-tuned custom model

**Current Implementation:** HTTP calls to NexusECSService (GPU container)

**Rationale:**
1. **GPU requirements** - Qwen-embedding-8B and ModernBERT require GPU acceleration
2. **Model management** - ECS container can manage model loading, caching, and inference
3. **Cost efficiency** - GPU instances can be shared across multiple requests
4. **Flexibility** - HTTP API allows model updates without Lambda redeployment

#### 12.3.3 Mapping Table Schema

**HLD Design:**
- PK: `controlKey`, SK: `mappedControlKey`
- Bidirectional entries (A→B and B→A) with TransactWrite
- Multiple GSIs for status, workflow, control+status queries

**Current Implementation:**
- PK: `mappingKey` (sorted concatenation of both control keys)
- Single entry per mapping
- Simplified GSI structure

**Rationale:**
1. **Simpler writes** - No need for TransactWrite for dual entries
2. **Consistent key** - Same mappingKey regardless of query direction
3. **Current query patterns** - Mappings are primarily queried by mappingKey or listed with filters
4. **Trade-off acknowledged** - "Get all mappings for controlX" requires scan or GSI; acceptable for current scale

#### 12.3.4 Enrichment Approach

**HLD Design:** MapControlFanout enriches controls and stores in ControlEnrichment database before mapping

**Current Implementation:**
- Enrichment is checked/created on-demand during mapping workflow
- Uses Claude via NexusStrandsAgentService for dynamic enrichment
- Multi-agent system (NexusEnrichmentAgent) generates framework-aware profiles

**Rationale:**
1. **Dynamic enrichment** - Claude provides richer, context-aware enrichment
2. **Profile-driven** - DynamicFrameworkProfileGenerator creates framework-specific profiles
3. **Lazy evaluation** - Controls are only enriched when needed for mapping

#### 12.3.5 Reasoning Generation

**HLD Design:** Mapper reasoning stored as part of MappingScores array with source attribution

**Current Implementation:**
- Reasoning generated as separate step in Step Functions Map state
- Stored as simple `reasoning` field in mapping
- Uses Claude via NexusStrandsAgentService

**Rationale:**
1. **Separation of concerns** - ML similarity scoring vs LLM reasoning are distinct operations
2. **Parallel execution** - Step Functions Map allows concurrent reasoning for multiple candidates
3. **Quality improvement** - Claude provides human-readable explanations

### 12.4 Not Yet Implemented (Per HLD)

| HLD Feature | Status | Notes |
|-------------|--------|-------|
| SIM/Ticket integration | ⏸️ Not implemented | QA workflow notifications via tickets |
| MappingUpdateNotifier | ⏸️ Not implemented | SNS/Slack notifications for new mappings |
| Idempotency database | ⏸️ Not implemented | For batch processor retry protection |
| ControlGuideIndex table | ⏸️ Not implemented | CG attribute indexing (commonControls, controlDomains, controlObjectives) |
| BYOC (Bring Your Own Control) | ⏸️ Not implemented | Custom framework support |
| Control versioning | ⏸️ Partial | controlVersion field exists but versioning workflow not implemented |
| A/B testing infrastructure | ⏸️ Not implemented | For science model comparison |

### 12.5 API Endpoint Alignment

| HLD Endpoint | Implementation | Notes |
|--------------|----------------|-------|
| `GET /frameworks` | ✅ Implemented | List all frameworks |
| `GET /frameworks/{name}` | ✅ Implemented | List versions |
| `GET /frameworks/{name}/{version}` | ✅ Implemented | Get specific framework |
| `PUT /frameworks/{name}/{version}` | ✅ Implemented | Create/update |
| `POST /frameworks/{name}/{version}/archive` | ✅ Implemented | Archive framework |
| `GET /controls` | ✅ Implemented | List controls |
| `GET /controls/{id}` | ✅ Implemented | Get control |
| `PUT /controls/{id}` | ✅ Implemented | Create/update |
| `POST /batchControls` | ✅ Implemented | Batch create (max 100) |
| `POST /controls/batchArchive` | ✅ Implemented | Batch archive |
| `GET /mappings` | ✅ Implemented | List mappings |
| `GET /mappings/{id}` | ✅ Implemented | Get mapping/status |
| `PUT /mappings/{id}` | ✅ Implemented | Update mapping |
| `POST /batchMappings` | ✅ Implemented | Batch create |

### 12.6 Role-Based Access Control (RBAC)

**HLD Roles:** Admin, QA, Consultant, Service

**Current Implementation:** NexusLambdaAuthorizer handles authentication; RBAC enforcement is application-level.

| Operation | HLD Roles | Implementation Status |
|-----------|-----------|----------------------|
| Create controls | Service, Admin | ✅ Enforced |
| Archive controls | Admin | ✅ Enforced |
| Create mappings | QA, Admin | ✅ Enforced |
| View approved mappings | All roles | ✅ Open |
| Submit reviews | QA | ✅ Enforced |
| Submit feedback | Consultant | ✅ Enforced |

---

## 13. Appendix

### 13.1 Job Status Lifecycle

```
PENDING → RUNNING → COMPLETED
                  → FAILED
```

### 13.2 Mapping Score Interpretation

| Score Range | Interpretation |
|-------------|----------------|
| 0.9 - 1.0 | Strong match |
| 0.7 - 0.9 | Good match |
| 0.5 - 0.7 | Moderate match |
| < 0.5 | Weak match (typically filtered) |

### 13.3 Common Frameworks

| Framework | Default Version |
|-----------|-----------------|
| NIST-SP-800-53 | R5 |
| NIST-CSF | 2.0 |
| SOC2 | 2017 |
| PCI-DSS | 4.0 |
| ISO-27001 | 2022 |
| HIPAA | 2013 |
| HITRUST | 11.0 |
| CIS | 8.0 |
