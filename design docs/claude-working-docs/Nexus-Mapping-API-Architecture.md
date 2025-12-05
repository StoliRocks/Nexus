# Nexus Mapping API Architecture

This document describes the complete flow of the Mapping API through each package in the Nexus system, from initial request to final result delivery.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [API Endpoints Summary](#api-endpoints-summary)
4. [Package Details](#package-details)
   - [NexusAsyncAPIHandlerLambda](#1-nexusasyncapihandlerlambda)
   - [NexusSqsTriggerLambda](#2-nexussqstriggerlambda)
   - [NexusDlqRedriveLambda](#3-nexusdlqredrivelambda)
   - [NexusStatusAPIHandlerLambda](#4-nexusstatusapihandlerlambda)
   - [NexusScienceOrchestratorLambda](#5-nexusscienceorchestratorlambda)
   - [NexusECSService](#6-nexusecsservice)
   - [NexusEnrichmentAgentLambda](#7-nexusenrichmentagentlambda)
   - [NexusStrandsAgentService](#8-nexusstrandsagentservice)
   - [NexusReasoningAgentLambda](#9-nexusreasoningagentlambda)
   - [NexusJobUpdaterLambda](#10-nexusjobupdaterlambda)
   - [NexusMappingAPIHandlerLambda](#11-nexusmappingapihandlerlambda)
   - [NexusApplicationInterface](#12-nexusapplicationinterface)
   - [NexusApplicationCommons](#13-nexusapplicationcommons)
5. [Complete Request Flow](#complete-request-flow)
6. [Database Schema](#database-schema)
7. [SQS Infrastructure](#sqs-infrastructure)
8. [Environment Variables](#environment-variables)

---

## Overview

The Nexus Mapping API enables semantic mapping between AWS service controls and industry compliance frameworks (NIST, SOC2, PCI-DSS). The system uses:

- **GPU-accelerated ML models** for embedding generation and semantic similarity
- **Multi-agent enrichment** for control text enhancement
- **LLM-powered reasoning** for mapping justification
- **Asynchronous processing** via AWS Step Functions

### Key Technologies

| Component | Technology |
|-----------|------------|
| Embeddings | Qwen-8B bi-encoder (4096-dim vectors) |
| Reranking | ModernBERT cross-encoder |
| Enrichment | Claude-powered multi-agent system (Strands) |
| Reasoning | Claude LLM reasoning generator |
| Orchestration | AWS Step Functions |
| Compute | Lambda (orchestration) + ECS (ML inference) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT REQUEST                                  │
│                    POST /api/v1/mappings (async)                            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                                           │
│                   + NexusLambdaAuthorizer                                    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   NexusAsyncAPIHandlerLambda                                 │
│   • Validate request format                                                  │
│   • Verify control/framework exist                                          │
│   • Create job record (PENDING) using Job DAO                               │
│   • Publish to MappingRequestQueue (SQS)                                    │
│   • Return 202 Accepted                                                     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SQS DURABILITY LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐     ┌─────────────────────┐     ┌────────────────┐  │
│  │ MappingRequest     │     │ MappingRequest      │     │ NexusDlqRedrive│  │
│  │      Queue         │────▶│       DLQ           │────▶│     Lambda     │  │
│  │ (7-day retention)  │     │ (14-day retention)  │     │ (manual retry) │  │
│  └─────────┬──────────┘     │  (after 3 failures) │     └────────┬───────┘  │
│            │                 └─────────────────────┘              │          │
│            │                                                      │          │
│            │◀─────────────────────────────────────────────────────┘          │
│            │                  (after bug fix deployed)                       │
│            ▼                                                                 │
│  ┌────────────────────┐                                                     │
│  │ NexusSqsTrigger    │                                                     │
│  │     Lambda         │                                                     │
│  │ • Start Step Fns   │                                                     │
│  │ • Update job→RUNNING│                                                    │
│  └─────────┬──────────┘                                                     │
│            │                                                                 │
└────────────┼─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      STEP FUNCTIONS WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐  │
│  │ ValidateControl  │───▶│ CheckEnrichment  │───▶│   Conditional        │  │
│  │  (ScienceOrch)   │    │   (ScienceOrch)  │    │   Choice             │  │
│  └──────────────────┘    └──────────────────┘    └──────────┬───────────┘  │
│                                                              │              │
│                          ┌───────────────────────────────────┼──────────┐   │
│                          │                                   │          │   │
│                          ▼                                   ▼          │   │
│           ┌──────────────────────────┐         ┌────────────────────┐  │   │
│           │  RunEnrichment           │         │   Skip Enrichment  │  │   │
│           │  (EnrichmentAgentLambda) │         │   (use cached)     │  │   │
│           │         │                │         └─────────┬──────────┘  │   │
│           │         ▼                │                   │             │   │
│           │  NexusStrandsAgentService│                   │             │   │
│           │  /api/v1/enrich          │                   │             │   │
│           └──────────────┬───────────┘                   │             │   │
│                          │                               │             │   │
│                          └───────────────┬───────────────┘             │   │
│                                          ▼                             │   │
│  ┌───────────────────────────────────────────────────────────────────┐│   │
│  │                  ScienceModel (ScienceOrchestratorLambda)         ││   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐   ││   │
│  │  │  Embed   │──▶│ Retrieve │──▶│  Rerank  │──▶│ Build Results│   ││   │
│  │  │ (Qwen)   │   │ (cosine) │   │(ModernBERT)  │              │   ││   │
│  │  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────────────┘   ││   │
│  │       │              │              │                            ││   │
│  │       └──────────────┴──────────────┘                            ││   │
│  │                      │                                           ││   │
│  │                      ▼                                           ││   │
│  │              NexusECSService (GPU)                               ││   │
│  │              /embed, /retrieve, /rerank                          ││   │
│  └───────────────────────────────────────────────────────────────────┘│   │
│                                          │                             │   │
│                                          ▼                             │   │
│  ┌───────────────────────────────────────────────────────────────────┐│   │
│  │                  Map State: Generate Reasoning                    ││   │
│  │                  (max 5 concurrent executions)                    ││   │
│  │                                                                   ││   │
│  │   ┌─────────────────────┐                                         ││   │
│  │   │ NexusReasoningAgent │───▶ NexusStrandsAgentService            ││   │
│  │   │      Lambda         │     /api/v1/reason                      ││   │
│  │   └─────────────────────┘     (Claude LLM)                        ││   │
│  └───────────────────────────────────────────────────────────────────┘│   │
│                                          │                             │   │
│                                          ▼                             │   │
│  ┌───────────────────────────────────────────────────────────────────┐│   │
│  │                  NexusJobUpdaterLambda                            ││   │
│  │  • Merge mappings + reasoning                                     ││   │
│  │  • Update job status (COMPLETED/FAILED)                          ││   │
│  └───────────────────────────────────────────────────────────────────┘│   │
│                                                                        │   │
└────────────────────────────────────────────────────────────────────────┘   │
                                                                              │
                                ┌─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLIENT POLLING                                        │
│                   GET /api/v1/mappings/{mappingId}                          │
│                                                                              │
│                   NexusStatusAPIHandlerLambda                               │
│                   • Returns job status + results                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints Summary

### Async Mapping Workflow

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| POST | `/api/v1/mappings` | NexusAsyncAPIHandlerLambda | Start async mapping job |
| GET | `/api/v1/mappings/{mappingId}` | NexusStatusAPIHandlerLambda | Get job status/results |

### Synchronous Mapping CRUD

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| GET | `/api/v1/mappings` | NexusMappingAPIHandlerLambda | List mappings |
| GET | `/api/v1/mappings/{mappingId}` | NexusMappingAPIHandlerLambda | Get mapping by key |
| PUT | `/api/v1/mappings/{mappingId}` | NexusMappingAPIHandlerLambda | Update mapping |
| POST | `/api/v1/batchMappings` | NexusMappingAPIHandlerLambda | Batch create (max 100) |
| PUT | `/api/v1/mappings/{mappingId}/archive` | NexusMappingAPIHandlerLambda | Archive mapping |

### Internal ECS Services

| Method | Endpoint | Service | Description |
|--------|----------|---------|-------------|
| POST | `/api/v1/embed` | NexusECSService | Generate Qwen embedding |
| POST | `/api/v1/retrieve` | NexusECSService | Cosine similarity search |
| POST | `/api/v1/rerank` | NexusECSService | Cross-encoder reranking |
| POST | `/api/v1/enrich` | NexusStrandsAgentService | Multi-agent enrichment |
| POST | `/api/v1/reason` | NexusStrandsAgentService | Reasoning generation |

---

## Package Details

### 1. NexusAsyncAPIHandlerLambda

**Location:** `NexusAsyncAPIHandlerLambda/`

**Purpose:** Entry point for async mapping requests. Validates input, creates job record, and publishes to SQS for durable processing.

**Request Format:**
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
| `validate_control_key_format()` | Validates pattern: `^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+#.+$` |
| `validate_framework_key_format()` | Validates pattern: `^[A-Za-z0-9._-]+#[A-Za-z0-9._-]+$` |
| `control_exists()` | Queries ControlKeyIndex GSI; returns suggestions if not found |
| `framework_exists()` | Queries Frameworks table; returns available frameworks if not found |
| `create_job()` | Creates job record using Job DAO with PENDING status and 7-day TTL |
| `enqueue_mapping_request()` | Publishes to MappingRequestQueue for durable processing |
| `start_workflow()` | Alias for enqueue_mapping_request (backward compatibility) |

**Service Class:**
```python
class AsyncMappingService:
    def __init__(
        self,
        dynamodb_resource: Optional[Any] = None,
        sqs_client: Optional[Any] = None,
        job_repository: Optional[JobRepository] = None,
        queue_url: Optional[str] = None,
    ):
        ...
```

**Dependencies:**
- `NexusApplicationInterface` - Job model, JobStatus enum
- `NexusApplicationCommons` - BaseRepository pattern

---

### 2. NexusSqsTriggerLambda

**Location:** `NexusSqsTriggerLambda/`

**Purpose:** SQS event consumer that starts Step Functions workflows. Provides durability - if Step Functions fails due to bugs requiring code fixes, requests are preserved in DLQ.

**SQS Event Input:**
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
| `start_workflow()` | Starts Step Functions execution for each SQS message |
| `JobRepository.update_status()` | Updates job status to IN_PROGRESS |

**SQS Configuration:**
- Event source: MappingRequestQueue
- Batch size: 1 (process one message at a time)
- Partial batch failure reporting: Enabled
- Max receive count: 3 (then moves to DLQ)

**Failure Handling:**
- If `start_execution` fails, message becomes visible again after visibility timeout
- After 3 failures, message moves to MappingRequestDLQ
- Messages preserved in DLQ for 14 days for retry after bug fixes

---

### 3. NexusDlqRedriveLambda

**Location:** `NexusDlqRedriveLambda/`

**Purpose:** Redrives failed messages from MappingRequestDLQ back to MappingRequestQueue after bug fixes are deployed.

**Invocation:** Manual or scheduled (not automatically triggered)

**Request Format:**
```json
{
  "dry_run": true,        // Optional: just count messages without redriving
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

**Dry Run Response:**
```json
{
  "statusCode": 200,
  "dry_run": true,
  "dlq_message_count": 30,
  "message": "DLQ contains 30 messages ready for redrive"
}
```

**Workflow:**
1. Get approximate message count from DLQ
2. Receive messages from DLQ (up to max_messages)
3. For each message: send to main queue, then delete from DLQ
4. Return count of successfully redriven messages

---

### 4. NexusStatusAPIHandlerLambda

**Location:** `NexusStatusAPIHandlerLambda/`

**Purpose:** Returns job status and results when completed.

**Response (PENDING/RUNNING):**
```json
{
  "mappingId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RUNNING",
  "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetFrameworkKey": "NIST-SP-800-53#R5",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:05:00Z"
}
```

**Response (COMPLETED):**
```json
{
  "mappingId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "controlKey": "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
  "targetFrameworkKey": "NIST-SP-800-53#R5",
  "result": {
    "mappings": [
      {
        "targetControlId": "AC-1",
        "targetControlKey": "NIST-SP-800-53#R5#AC-1",
        "similarityScore": 0.95,
        "rerankScore": 0.92,
        "reasoning": "Strong alignment due to..."
      }
    ]
  }
}
```

**Response (FAILED):**
```json
{
  "mappingId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "error": "Control not found in database"
}
```

---

### 3. NexusScienceOrchestratorLambda

**Location:** `NexusScienceOrchestratorLambda/`

**Purpose:** Orchestrates the ML pipeline (embed → retrieve → rerank) as Step Functions tasks.

**Actions:**

#### Action: `validate_control`
Verifies source control exists in database.

```python
# Input
{"action": "validate_control", "control_key": "AWS.EC2#1.0#PR.1"}

# Output
{"exists": true, "control": {...}, "control_key": "AWS.EC2#1.0#PR.1"}
```

#### Action: `check_enrichment`
Checks if enriched control text is cached.

```python
# Input
{"action": "check_enrichment", "control_key": "AWS.EC2#1.0#PR.1"}

# Output
{"exists": true, "enrichment": {"enriched_text": "..."}}
```

#### Action: `map_control`
Core ML pipeline execution.

```python
# Input
{
    "action": "map_control",
    "control_key": "AWS.EC2#1.0#PR.1",
    "target_framework_key": "NIST-SP-800-53#R5",
    "target_control_ids": ["AC-1", "AC-2"]  # Optional
}

# Output
{
    "mappings": [
        {
            "target_control_key": "NIST-SP-800-53#R5#AC-1",
            "target_control_id": "AC-1",
            "target_framework_key": "NIST-SP-800-53#R5",
            "similarity_score": 0.95,
            "rerank_score": 0.92,
            "text": "Access control policy and procedures"
        }
    ],
    "source_control_key": "AWS.EC2#1.0#PR.1",
    "target_framework_key": "NIST-SP-800-53#R5"
}
```

**ML Pipeline Steps:**

1. **Get Control Text** - Prefer enriched text from Enrichment table
2. **Generate Embedding** - Call `/embed` or use cached embedding
3. **Fetch Targets** - Query FrameworkControls by frameworkKey
4. **Generate Target Embeddings** - Batch embed all target controls
5. **Retrieve Candidates** - Cosine similarity search (top 20)
6. **Rerank Candidates** - Cross-encoder scoring with threshold filtering
7. **Build Results** - Combine similarity and rerank scores

**Service Class:**
```python
class ScienceOrchestratorService:
    def __init__(
        self,
        dynamodb_resource: Optional[Any] = None,
        controls_table_name: Optional[str] = None,
        frameworks_table_name: Optional[str] = None,
        enrichment_table_name: Optional[str] = None,
        embedding_cache_table_name: Optional[str] = None,
        science_client: Optional[ScienceClient] = None,
    ):
        ...
```

---

### 4. NexusECSService

**Location:** `NexusECSService/`

**Purpose:** GPU-accelerated ML inference for embeddings, similarity search, and reranking.

**Architecture:** FastAPI application on ECS with GPU instance (g4dn.xlarge or similar).

#### POST `/api/v1/embed`

Generates 4096-dimensional embeddings using Qwen bi-encoder.

```python
# Request
{
    "control_id": "IAM.21",
    "text": "Ensure IAM users are managed through centralized identity provider"
}

# Response
{
    "control_id": "IAM.21",
    "embedding": [0.023, -0.145, ...],  # 4096 floats
    "cache_hit": false
}
```

**Model:** `Qwen/Qwen2-7B-instruct`
- Output: 4096-dimensional normalized vector
- Performance: 50-100ms per embedding, <10ms cache hit

#### POST `/api/v1/retrieve`

Performs cosine similarity search over target embeddings.

```python
# Request
{
    "source_embedding": [...],  # 4096-dim normalized
    "target_embeddings": [[...], [...], ...],  # List of vectors
    "top_k": 50
}

# Response
{
    "candidates": [
        {"control_id": "0", "similarity": 0.95},
        {"control_id": "5", "similarity": 0.89},
        ...
    ]
}
```

**Performance:**
- 1,000 targets: <50ms
- 10,000 targets: <200ms

#### POST `/api/v1/rerank`

Cross-encoder reranking using ModernBERT.

```python
# Request
{
    "source_text": "Ensure IAM users are managed through centralized identity provider",
    "candidates": [
        {"control_id": "NIST-AC-1", "text": "Access control policy and procedures"},
        {"control_id": "NIST-AC-2", "text": "Account management"}
    ]
}

# Response
{
    "rankings": [
        {"control_id": "NIST-AC-1", "score": 0.92},
        {"control_id": "NIST-AC-2", "score": 0.78}
    ]
}
```

**Model:** `cross-encoder/mmarco-MiniLMv2-L12-H384-multilingual`
- Performance: 50 candidates = 2-3 seconds

#### Health Endpoints

| Endpoint | Purpose | When 200 |
|----------|---------|----------|
| GET `/health` | ALB health check | Always (during startup) |
| GET `/ready` | Readiness check | When models loaded |

---

### 5. NexusEnrichmentAgentLambda

**Location:** `NexusEnrichmentAgentLambda/`

**Purpose:** Step Functions task that enriches control text using multi-agent system.

**Flow:**
```python
# Step Functions Input
{
    "control_key": "NIST-SP-800-53#R5#AC-1",
    "control": {
        "title": "Access Control Policy",
        "description": "The organization develops, documents..."
    }
}

# Step Functions Output
{
    "control_key": "NIST-SP-800-53#R5#AC-1",
    "enriched_text": "Enhanced control description with security context...",
    "status": "success"
}
```

**Integration:**
- Calls NexusStrandsAgentService `/api/v1/enrich`
- Stores result in Enrichment table for caching
- HTTP timeout: 120 seconds (agent processing)

---

### 6. NexusStrandsAgentService

**Location:** `NexusStrandsAgentService/`

**Purpose:** ECS service running strands-based multi-agent system for enrichment and reasoning.

#### POST `/api/v1/enrich`

Multi-agent control enrichment.

```python
# Request
{
    "metadata": {
        "frameworkName": "NIST-SP-800-53",
        "frameworkVersion": "R5"
    },
    "control": {
        "shortId": "AC-1",
        "title": "Access Control Policy",
        "description": "The organization develops, documents..."
    },
    "frameworkProfile": {...}  # Optional
}

# Response
{
    "controlId": "AC-1",
    "enrichedInterpretation": {
        "enrichedText": "...",
        "securityObjective": "...",
        "complianceContext": "...",
        "awsServices": ["IAM", "AWS Organizations"],
        "validationRequirements": [...]
    },
    "agentOutputs": {...},
    "status": "success"
}
```

**Agent Pipeline (6 agents):**

| Agent | Purpose |
|-------|---------|
| Agent 1 | Objective classification |
| Agent 2 | Technical/Hybrid/Non-Technical filter |
| Agent 3 | Primary AWS services identification |
| Agent 4 | Security impact analysis |
| Agent 5 | Validation requirements |
| Master | Review and consolidation |

#### POST `/api/v1/reason`

Single mapping reasoning generation.

```python
# Request
{
    "sourceControlId": "AWS-IAM-001",
    "sourceText": "Ensure IAM policies are attached only to groups or roles",
    "mapping": {
        "targetControlId": "NIST-AC-1",
        "targetFramework": "NIST-SP-800-53",
        "text": "Access control policy and procedures",
        "similarityScore": 0.85,
        "rerankScore": 0.92
    }
}

# Response
{
    "sourceControlId": "AWS-IAM-001",
    "targetControlId": "NIST-AC-1",
    "reasoning": "This mapping demonstrates strong alignment because...",
    "status": "success"
}
```

#### POST `/api/v1/reason/batch`

Batch reasoning (max 20 mappings).

```python
# Request
{
    "sourceControlId": "AWS-IAM-001",
    "sourceText": "...",
    "mappings": [
        {"targetControlId": "NIST-AC-1", ...},
        {"targetControlId": "NIST-AC-2", ...}
    ]
}

# Response
{
    "results": [
        {"sourceControlId": "...", "targetControlId": "NIST-AC-1", "reasoning": "..."},
        {"sourceControlId": "...", "targetControlId": "NIST-AC-2", "reasoning": "..."}
    ],
    "total": 2,
    "successful": 2,
    "failed": 0
}
```

#### POST `/api/v1/profile/generate`

Generate framework profile for enhanced enrichment.

```python
# Request
{
    "frameworkName": "SOC-2",
    "sampleControls": [
        {"shortId": "CC1.1", "title": "Control Environment", "description": "..."},
        {"shortId": "CC1.2", "title": "Board Oversight", "description": "..."}
    ]
}

# Response
{
    "frameworkName": "SOC-2",
    "profile": {
        "objectives": [...],
        "scope": "...",
        "key_controls": [...],
        "terminology": {...}
    },
    "status": "success"
}
```

---

### 7. NexusReasoningAgentLambda

**Location:** `NexusReasoningAgentLambda/`

**Purpose:** Step Functions Map task that generates reasoning for each mapping.

**Execution:** Runs in Map state with max 5 concurrent executions.

```python
# Step Functions Input (per mapping)
{
    "source_control_id": "AWS-IAM-001",
    "source_text": "Ensure IAM policies are attached only to groups or roles",
    "mapping": {
        "target_control_id": "AC-1",
        "target_control_key": "NIST-SP-800-53#R5#AC-1",
        "target_framework_key": "NIST-SP-800-53#R5",
        "similarity_score": 0.95,
        "rerank_score": 0.92,
        "text": "Access control policy and procedures"
    }
}

# Step Functions Output
{
    "control_id": "AC-1",
    "reasoning": "This mapping demonstrates strong alignment...",
    "source_control_id": "AWS-IAM-001",
    "status": "success"
}
```

---

### 8. NexusJobUpdaterLambda

**Location:** `NexusJobUpdaterLambda/`

**Purpose:** Final Step Functions task that updates job record with results or errors.

#### Success Path

```python
# Input
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "COMPLETED",
    "mappings": [...],  # From ScienceOrchestrator
    "reasoning": [...]  # From Reasoning Map state
}

# Action
# 1. Merge mappings with reasoning results
# 2. Update job record with status=COMPLETED
# 3. Store enriched mappings with reasoning
```

#### Failure Path

```python
# Input
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "FAILED",
    "error": {
        "Cause": "Control not found in database",
        "Error": "ControlNotFoundError"
    }
}

# Action
# 1. Extract error message
# 2. Update job record with status=FAILED
# 3. Store error_message for client retrieval
```

---

### 9. NexusMappingAPIHandlerLambda

**Location:** `NexusMappingAPIHandlerLambda/`

**Purpose:** Synchronous CRUD operations for mapping records.

**Routes:**

| Method | Path | Function |
|--------|------|----------|
| GET | `/mappings` | `list_mappings()` |
| GET | `/mappings/{mappingId}` | `get_mapping()` |
| GET | `/controls/{controlId}/mappings` | `get_mappings_for_control()` |
| POST | `/batchMappings` | `batch_create_mappings()` |
| PUT | `/mappings/{mappingId}/archive` | `archive_mapping()` |

**Batch Create Request:**
```json
{
  "mappings": [
    {
      "source_control_key": "AWS.EC2#1.0#PR.1",
      "target_control_key": "NIST-SP-800-53#R5#AC-1",
      "similarity_score": 0.95,
      "rerank_score": 0.92,
      "reasoning": "Strong alignment due to..."
    }
  ]
}
```

**Mapping Key Generation:**
```python
def generate_mapping_key(key1: str, key2: str) -> str:
    """Creates normalized key by sorting and concatenating."""
    keys = sorted([key1, key2])
    return f"{keys[0]}|{keys[1]}"
```

---

### 10. NexusApplicationInterface

**Location:** `NexusApplicationInterface/api/v1/models/`

**Purpose:** Pydantic models and data contracts for API/state machine.

**Key Models:**

```python
# mapping.py
class Mapping(BaseModel):
    control_key: str
    mapped_control_key: str
    mapping_key: str  # Normalized (sorted) key
    arn: str
    mapping_workflow_key: str
    timestamp: str
    status: MappingStatus  # APPROVED, PENDING_REVIEW, REJECTED, ARCHIVED
    created_by: CreatorInfo
    last_modified_by: CreatorInfo
    additional_info: Optional[List[MappingAdditionalInfo]]

# job.py
class Job(BaseModel):
    job_id: str
    status: JobStatus  # PENDING, RUNNING, COMPLETED, FAILED
    control_key: str
    target_framework_key: str
    created_at: str
    updated_at: str
    target_control_ids: Optional[List[str]]
    ttl: Optional[int]  # Unix timestamp (7 days)
    mappings: Optional[List[Dict[str, Any]]]
    error: Optional[Dict[str, Any]]

# requests.py
class BatchMappingsCreateRequest(BaseModel):
    mappings: List[MappingCreateItem]  # Max 100

class MappingCreateItem(BaseModel):
    source_control_key: str
    target_control_key: str
    similarity_score: Optional[float]
    rerank_score: Optional[float]
    reasoning: Optional[str]
```

**Enums:**

```python
class MappingStatus(str, Enum):
    APPROVED = "APPROVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

---

### 11. NexusApplicationCommons

**Location:** `NexusApplicationCommons/dynamodb/`

**Purpose:** Shared utilities including response builders.

**Response Builder Functions:**

```python
def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Returns 200 OK with JSON body."""

def created_response(data: Any) -> Dict[str, Any]:
    """Returns 201 Created."""

def accepted_response(data: Any) -> Dict[str, Any]:
    """Returns 202 Accepted (for async operations)."""

def not_found_response(resource: str, identifier: str) -> Dict[str, Any]:
    """Returns 404 Not Found."""

def validation_error_response(message: str, field: str = None) -> Dict[str, Any]:
    """Returns 400 Bad Request with validation error."""

def error_response(message: str, status_code: int = 400, error_code: str = None) -> Dict:
    """Returns custom error response."""
```

**Response Format:**
```python
{
    "statusCode": 200,
    "headers": {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    },
    "body": "{...JSON serialized...}"
}
```

---

## Complete Request Flow

### Async Mapping Request (POST /api/v1/mappings)

```
1. CLIENT REQUEST
   POST /api/v1/mappings
   {
     "control_key": "AWS.EC2#1.0#PR.1",
     "target_framework_key": "NIST-SP-800-53#R5"
   }

2. NexusAsyncAPIHandlerLambda
   ├─ Parse request body
   ├─ Validate control_key format (regex)
   ├─ Validate framework_key format (regex)
   ├─ Query FrameworkControls: verify control exists
   ├─ Query Frameworks: verify framework exists
   ├─ Create job record (status=PENDING, TTL=7 days)
   ├─ Start Step Functions execution
   └─ Return 202 Accepted

3. STEP FUNCTIONS WORKFLOW

   State 1: ValidateControl
   ├─ NexusScienceOrchestratorLambda (action=validate_control)
   └─ Returns: {exists: true, control: {...}}

   State 2: CheckEnrichment
   ├─ NexusScienceOrchestratorLambda (action=check_enrichment)
   └─ Returns: {exists: true/false, enrichment: {...}}

   State 3: Conditional Choice
   ├─ If NOT enriched:
   │  └─ RunEnrichment
   │     ├─ NexusEnrichmentAgentLambda
   │     ├─ HTTP POST → NexusStrandsAgentService /enrich
   │     ├─ Multi-agent processing (6 agents)
   │     ├─ Store in Enrichment table
   │     └─ Returns: {enriched_text: "..."}
   └─ If enriched:
      └─ Skip to next state

   State 4: ScienceModel
   ├─ NexusScienceOrchestratorLambda (action=map_control)
   │
   │  Step 1: Get source control text
   │  ├─ Check Enrichment table (prefer enriched)
   │  └─ Fallback to FrameworkControls description
   │
   │  Step 2: Generate embedding
   │  ├─ Check EmbeddingCache table
   │  ├─ If miss: POST → NexusECSService /embed
   │  └─ Cache result
   │
   │  Step 3: Fetch target controls
   │  ├─ Query FrameworkControls by frameworkKey
   │  └─ Optional: Filter by target_control_ids
   │
   │  Step 4: Generate target embeddings
   │  └─ For each target: POST → /embed (benefits from cache)
   │
   │  Step 5: Retrieve candidates
   │  ├─ POST → NexusECSService /retrieve
   │  └─ Returns top 20 by cosine similarity
   │
   │  Step 6: Rerank candidates
   │  ├─ POST → NexusECSService /rerank
   │  └─ Cross-encoder scoring with threshold
   │
   │  Step 7: Build results
   │  └─ Returns: {mappings: [...], source_control_key, target_framework_key}

   State 5: Map State (Reasoning)
   ├─ Max 5 concurrent executions
   └─ For each mapping:
      ├─ NexusReasoningAgentLambda
      ├─ HTTP POST → NexusStrandsAgentService /reason
      └─ Returns: {reasoning: "...", control_id: "..."}

   State 6: UpdateJob
   ├─ NexusJobUpdaterLambda
   ├─ Merge mappings with reasoning
   └─ Update job status=COMPLETED

   Error Handler:
   └─ NexusJobUpdaterLambda (status=FAILED)

4. CLIENT POLLING
   GET /api/v1/mappings/{mappingId}
   ├─ NexusStatusAPIHandlerLambda
   ├─ Query MappingJobs table
   └─ Return status + results
```

---

## Database Schema

### MappingJobs Table

| Attribute | Type | Description |
|-----------|------|-------------|
| job_id (PK) | String | UUID |
| status | String | PENDING, RUNNING, COMPLETED, FAILED |
| control_key | String | Source control key |
| target_framework_key | String | Target framework key |
| target_control_ids | List | Optional specific controls |
| created_at | String | ISO timestamp |
| updated_at | String | ISO timestamp |
| completed_at | String | ISO timestamp (on completion) |
| failed_at | String | ISO timestamp (on failure) |
| mappings | List | Result mappings with reasoning |
| error_message | String | Error details (on failure) |
| ttl | Number | Unix timestamp (7 days) |

### ControlMappings Table

| Attribute | Type | Description |
|-----------|------|-------------|
| controlKey (PK) | String | Source control key |
| mappedControlKey (SK) | String | Target control key |
| mappingKey | String | Normalized key (sorted) |
| arn | String | ARN with mapping key |
| status | String | APPROVED, PENDING_REVIEW, REJECTED, ARCHIVED |
| similarity_score | Number | Cosine similarity (0-1) |
| rerank_score | Number | Cross-encoder score (0-1) |
| reasoning | String | LLM-generated justification |
| created_by | Map | Creator info |
| timestamp | String | ISO timestamp |

**GSIs:**
- MappingKeyIndex: mappingKey → controlKey, mappedControlKey
- StatusIndex: status → controlKey, mappedControlKey
- ControlStatusIndex: controlKey + status

### Enrichment Table

| Attribute | Type | Description |
|-----------|------|-------------|
| control_id (PK) | String | Control key |
| original_text | String | Original description |
| enriched_text | String | Enhanced description |
| enrichment_data | Map | Full agent outputs |
| version | String | Enrichment version |
| created_at | String | ISO timestamp |

### EmbeddingCache Table

| Attribute | Type | Description |
|-----------|------|-------------|
| control_id (PK) | String | Control key |
| model_version (SK) | String | Model version (e.g., "v1") |
| embedding | List | 4096 floats |
| created_at | String | ISO timestamp |

---

## SQS Infrastructure

### MappingRequestQueue

**Type:** Standard SQS Queue

**Purpose:** Durable buffer for async mapping requests. Provides durability - requests are preserved even if Step Functions fails.

| Property | Value | Description |
|----------|-------|-------------|
| Visibility Timeout | 60 seconds | Time for SQS Trigger Lambda to process |
| Message Retention | 7 days | How long messages are kept |
| Max Receive Count | 3 | Retries before moving to DLQ |
| Delivery Delay | 0 | No delay |
| Encryption | AWS managed | Server-side encryption |

### MappingRequestDLQ

**Type:** Standard SQS Queue (Dead Letter Queue)

**Purpose:** Stores failed messages for retry after bug fixes are deployed.

| Property | Value | Description |
|----------|-------|-------------|
| Message Retention | 14 days | Extended retention for manual retry |
| Encryption | AWS managed | Server-side encryption |

### CloudWatch Alarms

| Alarm | Condition | Action |
|-------|-----------|--------|
| DLQ Not Empty | ApproximateNumberOfMessages > 0 | Alert on failures |
| Queue Backlog | ApproximateNumberOfMessages > 100 | Alert on processing delays |
| Message Age | ApproximateAgeOfOldestMessage > 3600s | Alert on stuck messages |

### Message Flow

```
AsyncAPIHandler                    MappingRequestQueue           SqsTriggerLambda
     │                                    │                            │
     │ ──── publish message ────────────▶ │                            │
     │                                    │ ◀──── receive (batch=1) ─── │
     │                                    │                            │
     │                                    │     ┌── success ──▶ delete message
     │                                    │     │
     │                                    │     └── failure ──▶ retry (up to 3x)
     │                                    │                            │
     │                                    │                            ▼
     │                                    │              MappingRequestDLQ
     │                                    │              (after 3 failures)
     │                                    │                            │
     │                                    │           ┌────────────────┘
     │                                    │           │ DlqRedriveLambda
     │                                    │ ◀─────────┘ (manual, after fix)
```

---

## Environment Variables

| Variable | Packages | Default | Description |
|----------|----------|---------|-------------|
| JOB_TABLE_NAME | Async, SqsTrigger, Status, Updater | MappingJobs | Jobs table name |
| MAPPING_REQUEST_QUEUE_URL | Async | Required | SQS queue URL for durable processing |
| STATE_MACHINE_ARN | SqsTrigger | Required | Step Functions ARN |
| DLQ_URL | DlqRedrive | Required | Dead letter queue URL |
| MAIN_QUEUE_URL | DlqRedrive | Required | Main queue URL for redrive |
| FRAMEWORKS_TABLE_NAME | Async, Science | Frameworks | Frameworks table |
| CONTROLS_TABLE_NAME | Async, Science | FrameworkControls | Controls table |
| ENRICHMENT_TABLE_NAME | Enrichment, Science | Enrichment | Enrichment cache |
| EMBEDDING_CACHE_TABLE_NAME | Science | EmbeddingCache | Embedding cache |
| MAPPINGS_TABLE_NAME | Mapping CRUD | ControlMappings | Mappings table |
| SCIENCE_API_ENDPOINT | Science | Required | ECS ML service URL |
| STRANDS_SERVICE_ENDPOINT | Enrichment, Reasoning | Required | Strands service URL |
| USE_MOCK_SCIENCE | Science | false | Enable mock mode |
| MODEL_VERSION | Science | v1 | Embedding model version |
| ENRICHMENT_VERSION | Enrichment | v1 | Enrichment version |

---

## Key Design Patterns

### Lambda Handler Pattern

```python
# handler.py
def lambda_handler(event: dict, context: Any) -> dict:
    service = SomeService()
    return service.some_method(...)

api_endpoint_handler = lambda_handler  # BATS alias

# service.py
class SomeService:
    def __init__(
        self,
        dynamodb_resource: Optional[Any] = None,
        table_name: Optional[str] = None,
    ):
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name or TABLE_NAME)
```

### Request Validation Pattern

```python
from pydantic import ValidationError

try:
    body = json.loads(event.get("body", "{}"))
    request = SomeRequest.model_validate(body)
except ValidationError as e:
    return validation_error_response(e.errors()[0]["msg"])
```

### Database Key Patterns

| Key Type | Format | Example |
|----------|--------|---------|
| frameworkKey | `{name}#{version}` | `NIST-SP-800-53#R5` |
| controlKey | `{frameworkKey}#{controlId}` | `NIST-SP-800-53#R5#AC-1` |
| mappingKey | `{sorted(key1, key2)}` | `AWS.EC2#1.0#PR.1|NIST-SP-800-53#R5#AC-1` |

### ARN Format

```
arn:aws:nexus:::resource/{key}
```

---

*Generated for the Nexus Compliance Mapping Pipeline*
