# NexusReasoningAgent

Generates human-readable rationale for control mappings using Claude via AWS Bedrock. Explains why an AWS control maps to a framework control based on semantic similarity and cross-encoder scores.

## Overview

This package provides reasoning generation that:

1. Takes a source AWS control and target framework control
2. Considers similarity scores from embedding and reranking
3. Generates a concise explanation of the mapping relationship

The reasoning is used in the Nexus UI to help compliance teams understand and validate automated mappings.

## Installation

```bash
# Install with pip
pip install -e .

# Or with Brazil
brazil-build
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `REASONING_MODEL_ID` | Claude model ID | `anthropic.claude-3-haiku-20240307-v1:0` |

## Usage

### Simple Function Call

For one-off reasoning generation:

```python
from nexus_reasoning_agent import generate_reasoning

reasoning = generate_reasoning(
    source_control_id="AWS-CONFIG-001",
    source_text="Ensures S3 buckets have versioning enabled to protect against accidental deletion",
    mapping={
        "target_control_id": "SC-28",
        "target_framework": "NIST-800-53",
        "text": "Protection of information at rest",
        "similarity_score": 0.85,
        "rerank_score": 0.92,
    }
)

print(reasoning)
# "This AWS control maps to NIST SC-28 because both address data protection.
#  The S3 versioning requirement directly supports the protection of information
#  at rest by enabling recovery from accidental or malicious modifications.
#  The high similarity (85%) and rerank (92%) scores indicate strong semantic
#  alignment between the controls."
```

### Class-Based Usage

For batch processing or custom configuration:

```python
from nexus_reasoning_agent import ReasoningGenerator

generator = ReasoningGenerator(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    max_tokens=300,
    temperature=0.0
)

# Single mapping
reasoning = generator.generate_reasoning(
    source_control_id="IAM.21",
    source_text="Ensure IAM users are managed through centralized identity provider",
    mapping={
        "target_control_id": "AC-2",
        "target_framework": "NIST-800-53",
        "text": "Account Management",
        "similarity_score": 0.78,
        "rerank_score": 0.85,
    }
)
```

### Batch Processing

Process multiple mappings for the same source control:

```python
mappings = [
    {
        "target_control_id": "AC-2",
        "target_framework": "NIST-800-53",
        "text": "Account Management",
        "similarity_score": 0.78,
        "rerank_score": 0.85,
    },
    {
        "target_control_id": "AC-3",
        "target_framework": "NIST-800-53",
        "text": "Access Enforcement",
        "similarity_score": 0.72,
        "rerank_score": 0.79,
    },
]

results = generator.generate_batch_reasoning(
    source_control_id="IAM.21",
    source_text="Ensure IAM users are managed through centralized identity provider",
    mappings=mappings
)

for result in results:
    print(f"{result['control_id']}: {result['reasoning']}")
    # AC-2: This AWS control maps to NIST AC-2 because...
    # AC-3: This AWS control maps to NIST AC-3 because...
```

### Consolidated Reasoning

For efficiency, generate reasoning for all mappings in a single API call:

```python
consolidated = generator.generate_consolidated_reasoning(
    source_control_id="IAM.21",
    source_text="Ensure IAM users are managed through centralized identity provider",
    mappings=mappings
)

print(consolidated)
# Returns a single string with reasoning for all mappings
```

## Prompt Templates

The package provides customizable prompt builders:

```python
from nexus_reasoning_agent import (
    build_mapping_rationale_prompt,
    build_batch_reasoning_prompt,
)

# Single mapping prompt
prompt = build_mapping_rationale_prompt(
    source_control_id="IAM.21",
    source_text="...",
    target_control_id="AC-2",
    target_framework="NIST-800-53",
    target_text="...",
    similarity_score=0.78,
    rerank_score=0.85,
)

# Batch prompt
batch_prompt = build_batch_reasoning_prompt(
    source_control_id="IAM.21",
    source_text="...",
    mappings=[...],
)
```

## Integration with Step Functions

This package is used in the Nexus mapping pipeline:

```python
# In Lambda handler
from nexus_reasoning_agent import ReasoningGenerator

def handler(event, context):
    generator = ReasoningGenerator()

    source = event["source_control"]
    mappings = event["mappings"]

    results = generator.generate_batch_reasoning(
        source_control_id=source["controlId"],
        source_text=source["description"],
        mappings=mappings
    )

    return {"reasoning_results": results}
```

## Architecture

```
NexusReasoningAgent/
├── src/nexus_reasoning_agent/
│   ├── __init__.py           # Package exports
│   ├── reasoning_generator.py # Main generator class
│   └── prompts.py            # Prompt templates
├── test/
│   └── test_reasoning_generator.py
├── pyproject.toml
└── Config                    # Brazil build
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=nexus_reasoning_agent --cov-report=html

# Run specific test
pytest test/test_reasoning_generator.py -v
```

## Performance

| Operation | Model | Latency | Cost |
|-----------|-------|---------|------|
| Single reasoning | claude-3-haiku | 500-800ms | ~$0.0001 |
| Batch (10 mappings) | claude-3-haiku | 5-8s | ~$0.001 |
| Consolidated (10) | claude-3-haiku | 1-2s | ~$0.0003 |

Using `generate_consolidated_reasoning` is recommended for multiple mappings as it's faster and cheaper.

## Dependencies

- Python 3.11+
- boto3 (AWS SDK)
- AWS Bedrock access with Claude models
