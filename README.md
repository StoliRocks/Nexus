# Nexus

AWS compliance control mapping pipeline that maps AWS service controls to industry frameworks (NIST, SOC2, PCI-DSS) using GPU-accelerated ML models and Claude LLM agents for semantic retrieval and reasoning.

## Architecture

```
API Gateway → Lambda Handlers → SQS Queue → Step Functions → ECS GPU Service
                                   │              │
                                   │              ├── Enrichment Agent (Claude)
                                   │              ├── Reasoning Agent (Claude)
                                   │              └── Job Updater
                                   │
                                   └── DLQ (failed messages) → Redrive Lambda
```

## Key Features

- **Semantic Control Mapping**: Maps AWS controls to compliance frameworks using ML-powered similarity matching
- **GPU-Accelerated ML**: Qwen-embedding-8B for 4096-dim embeddings, ModernBERT cross-encoder for reranking
- **Multi-Agent Enrichment**: Strands-based agents for control interpretation and context enrichment
- **Reasoning Generation**: LLM-powered explanations for why controls map to framework requirements
- **Durable Request Processing**: SQS-based ingestion with DLQ for failed message recovery

## Monorepo Structure

| Package | Description |
|---------|-------------|
| `NexusApplicationInterface` | Pydantic models and data contracts |
| `NexusApplicationCommons` | Shared utilities (response builders, DynamoDB helpers) |
| `NexusEnrichmentAgent` | Multi-agent enrichment system using strands |
| `NexusReasoningAgent` | Reasoning generator for mapping rationale |
| `NexusApplicationPipelineCDK` | TypeScript CDK infrastructure |
| `NexusECSService` | GPU ML inference service (Qwen, ModernBERT) |
| `NexusStrandsAgentService` | ECS container for strands-based agents |
| `NexusFrameworkAPIHandlerLambda` | Framework CRUD operations |
| `NexusControlAPIHandlerLambda` | Control CRUD operations |
| `NexusMappingAPIHandlerLambda` | Mapping CRUD operations |
| `NexusMappingReviewAPIHandlerLambda` | Review operations |
| `NexusMappingFeedbackAPIHandlerLambda` | Feedback operations |
| `NexusAsyncAPIHandlerLambda` | Async job creation (POST /mappings) |
| `NexusStatusAPIHandlerLambda` | Job status queries |
| `NexusScienceOrchestratorLambda` | ML pipeline orchestration |
| `NexusEnrichmentAgentLambda` | Enrichment Step Functions task |
| `NexusReasoningAgentLambda` | Reasoning Step Functions task |
| `NexusJobUpdaterLambda` | Job status updates |
| `NexusSqsTriggerLambda` | SQS consumer, starts Step Functions |
| `NexusDlqRedriveLambda` | DLQ message redrive utility |
| `NexusLambdaAuthorizer` | API Gateway custom authorizer |
| `DefaultAPIEndpointHandlerLambda` | Default/fallback API handler |
| `design docs/` | Architecture and design documentation |

## API Endpoints

### Frameworks
- `GET /api/v1/frameworks` - List all frameworks
- `GET /api/v1/frameworks/{name}/{version}` - Get specific framework
- `PUT /api/v1/frameworks/{name}/{version}` - Create/update framework

### Controls
- `GET /api/v1/frameworks/{name}/{version}/controls` - List controls
- `PUT /api/v1/frameworks/{name}/{version}/controls/{controlId}` - Create/update control
- `POST /api/v1/frameworks/{name}/{version}/batchControls` - Batch create (max 100)

### Mappings
- `POST /api/v1/mappings` - Start async mapping workflow (returns 202)
- `GET /api/v1/mappings/{mappingId}` - Get mapping status/results
- `PUT /api/v1/mappings/{mappingId}` - Update mapping

### ML Service (ECS)
- `POST /api/v1/embed` - Generate 4096-dim Qwen embedding
- `POST /api/v1/retrieve` - Cosine similarity search
- `POST /api/v1/rerank` - Cross-encoder ModernBERT reranking

### Agent Service (ECS)
- `POST /api/v1/enrich` - Enrich control via multi-agent system
- `POST /api/v1/reason` - Generate mapping reasoning

## Build Commands

```bash
# Build
brazil-build

# Test
brazil-build test
brazil-build test --addopts="-k test_pattern"

# Code quality
brazil-build format        # black + isort
brazil-build mypy          # Type checking
brazil-build lint          # flake8

# CDK
cd NexusApplicationPipelineCDK
npm run build
npx cdk synth
```

## Key Patterns

**Database Keys:**
- `frameworkKey`: `frameworkName#version` (e.g., `NIST-SP-800-53#R5`)
- `controlKey`: `frameworkKey#controlId` (e.g., `NIST-SP-800-53#R5#AC-1`)
- `mappingKey`: `controlKey1|controlKey2` (sorted concatenation)

**Async Mapping Flow:**
```
POST /mappings → AsyncHandler → SQS Queue → SqsTriggerLambda → Step Functions
                  (PENDING)      (durable)      (RUNNING)

Step Functions: ValidateControl → CheckEnrichment → [RunEnrichment] → ScienceModel → Map(Reasoning) → JobUpdater → End
```

## Deployment Environments

| Stage | Account | Description |
|-------|---------|-------------|
| Beta | 909139952351 | Development |
| Gamma | 098092129359 | Pre-production |
| Prod | 305345571965 | Production |

## License

Proprietary - Internal use only
