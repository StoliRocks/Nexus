# NexusEnrichmentAgent

Multi-agent enrichment system for control mapping using Claude via AWS Bedrock. Generates semantic enrichments for framework controls and AWS controls to improve mapping accuracy.

## Overview

This package provides profile-driven multi-agent systems that:

1. **Generate Framework Profiles**: Analyze sample controls to understand framework characteristics
2. **Enrich Framework Controls**: Extract objectives, technical requirements, security impact
3. **Enrich AWS Controls**: Identify compliance mappings and implementation details

The enrichment uses 5 specialized agents orchestrated by a master agent, with framework-specific guidance applied to each agent's prompts.

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
| `BEDROCK_MODEL_ID` | Claude model ID | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |

For cross-account Bedrock access, set session parameters:

```python
session_params = {
    "region_name": "us-east-1",
    "profile_name": "bedrock-profile",  # Optional
}
```

## Usage

### Generate Framework Profile

Before enriching controls, generate a profile from sample controls:

```python
from nexus_enrichment_agent import DynamicFrameworkProfileGenerator

# Initialize with framework name
profiler = DynamicFrameworkProfileGenerator(
    framework_name="NIST-800-53",
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)

# Generate profile from sample controls (5-10 recommended)
sample_controls = [
    {
        "shortId": "AC-1",
        "title": "Access Control Policy and Procedures",
        "description": "Develop, document, and disseminate access control policy..."
    },
    {
        "shortId": "AC-2",
        "title": "Account Management",
        "description": "Define and document account management procedures..."
    },
    # ... more samples
]

profile = await profiler.generate_profile(sample_controls)
# Returns: {
#   "framework_name": "NIST-800-53",
#   "agent_context": {...},
#   "enrichment_guidance": {...},
#   "language_analysis": {...}
# }
```

### Enrich Framework Controls

Use the generated profile to enrich controls:

```python
from nexus_enrichment_agent import ProfileDrivenMultiAgentProcessor

# Initialize with framework profile
processor = ProfileDrivenMultiAgentProcessor(
    framework_name="NIST-800-53",
    framework_profile=profile
)

# Enrich a control
control = {
    "shortId": "AC-3",
    "title": "Access Enforcement",
    "description": "Enforce approved authorizations for logical access..."
}

result = processor.interpret_control_intent(
    metadata={"framework": "NIST-800-53", "version": "R5"},
    control=control
)

# Returns: {
#   "enriched_interpretation": "{...JSON with all enrichment fields...}",
#   "agent_outputs": {
#     "agent1_objective_classification": "...",
#     "agent2_technical_filter": "...",
#     "agent3_technical_requirements": "...",
#     "agent4_security_impact": "...",
#     "agent5_validation_requirements": "..."
#   },
#   "framework_profile_applied": {...},
#   "status": "success"
# }
```

### Enrich AWS Controls

```python
from nexus_enrichment_agent import (
    AWSControlProfileGenerator,
    ProfileDrivenAWSProcessor
)

# Generate AWS-specific profile
aws_profiler = AWSControlProfileGenerator()
aws_profile = await aws_profiler.generate_profile(sample_aws_controls)

# Process AWS controls
aws_processor = ProfileDrivenAWSProcessor(
    profile=aws_profile
)

result = aws_processor.enrich_aws_control(
    control={
        "controlId": "IAM.21",
        "title": "Ensure IAM users are managed through centralized identity",
        "description": "This control checks whether IAM users are managed..."
    }
)
```

## Agent Architecture

The enrichment system uses 5 specialized agents plus a master reviewer:

| Agent | Purpose | Output |
|-------|---------|--------|
| Agent 1 | Objective Classification | Primary objective, scope, category |
| Agent 2 | Technical Filter | Implementation type, AWS mappability |
| Agent 3 | Technical Requirements | Primary AWS services, features |
| Agent 4 | Security Impact | Threats, attack vectors, remediation |
| Agent 5 | Validation Requirements | Assessment methods, evidence |
| Master | Review & Consolidate | Validated combined output |

Agents run in parallel for efficiency, with the master agent reviewing for consistency.

## Framework Profile Structure

```python
{
    "framework_name": "NIST-800-53",
    "agent_context": {
        "domain": "Federal Information Security",
        "regulatory_body": "NIST",
        "control_style": "Prescriptive with flexibility"
    },
    "enrichment_guidance": {
        "enrichment_philosophy": "Focus on implementation evidence...",
        "agent_guidance": [
            {
                "agent": "agent1",
                "emphasize": "Federal compliance requirements",
                "skip_if": "Control is organizational only"
            },
            # ... guidance for each agent
        ]
    },
    "language_analysis": {
        "control_focus": {
            "primary_focus": "Risk-based security controls",
            "abstraction_level": "High with implementation flexibility"
        },
        "control_structure": {
            "typical_format": "Requirement + supplemental guidance"
        }
    }
}
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=nexus_enrichment_agent --cov-report=html
```

## Dependencies

- Python 3.11+
- strands (agent framework)
- boto3 (AWS SDK)
- AWS Bedrock access with Claude models
