# Nexus Support Guide - Design Document

## Overview

This design document outlines the structure and content for a comprehensive Nexus Support Guide. The guide will be a single markdown document that serves as the primary reference for support engineers troubleshooting and operating the Nexus compliance control mapping platform.

The support guide consolidates information from existing documentation (Package Architecture Guide, README files) with operational procedures, troubleshooting runbooks, and quick reference materials.

## Architecture

### Document Structure

The support guide will be organized as a single markdown file with the following major sections:

```
NEXUS-SUPPORT-GUIDE.md
├── 1. System Overview
│   ├── Architecture Diagrams
│   ├── Package Inventory
│   └── Data Flow
├── 2. API Reference
│   ├── Framework APIs
│   ├── Control APIs
│   ├── Mapping APIs
│   └── Error Codes
├── 3. Database Reference
│   ├── Table Schemas
│   ├── Key Patterns
│   └── Query Examples
├── 4. Lambda Troubleshooting
│   ├── Error Patterns
│   ├── CloudWatch Queries
│   └── Environment Variables
├── 5. Step Functions Troubleshooting
│   ├── Workflow Steps
│   ├── Failure Scenarios
│   └── Remediation
├── 6. ECS Service Troubleshooting
│   ├── NexusECSService
│   ├── NexusStrandsAgentService
│   └── Performance Baselines
├── 7. Environment Configuration
│   ├── Deployment Stages
│   ├── Access Procedures
│   └── Health Verification
├── 8. Runbooks
│   ├── Mapping Job Issues
│   ├── ECS Service Issues
│   ├── Performance Issues
│   └── AWS Service Issues
├── 9. Monitoring & Alerting
│   ├── CloudWatch Alarms
│   ├── Key Metrics
│   └── Escalation Procedures
└── 10. Quick Reference
    ├── Service Endpoints
    ├── Table Names
    ├── CLI Commands
    └── Contacts
```

### Content Sources

| Section | Primary Sources |
|---------|-----------------|
| System Overview | Package Architecture Guide, README files |
| API Reference | Lambda handler code, existing API docs |
| Database Reference | Package Architecture Guide, service.py files |
| Lambda Troubleshooting | Handler patterns, environment variables |
| Step Functions | Package Architecture Guide, workflow definitions |
| ECS Services | NexusECSService/README.md, NexusStrandsAgentService/README.md |
| Environment Config | CDK stack, deployment documentation |
| Runbooks | New content based on common failure patterns |
| Monitoring | CDK alarms, operational experience |
| Quick Reference | Consolidated from all sources |

## Components and Interfaces

### Support Guide Generator (Optional Future Enhancement)

For maintainability, the support guide could be generated from source files. However, for the initial implementation, the guide will be manually authored as a static markdown document.

### Document Sections

#### 1. System Overview Component

Content includes:
- High-level architecture diagram (ASCII art for portability)
- Async mapping pipeline diagram
- Package inventory table with 20+ packages
- Data flow descriptions for sync and async operations

#### 2. API Reference Component

Content includes:
- Framework endpoints (5 endpoints)
- Control endpoints (5 endpoints)
- Mapping endpoints (4 endpoints)
- Review/Feedback endpoints (referenced)
- Error code table with meanings and resolution hints

#### 3. Database Reference Component

Content includes:
- 8 DynamoDB tables with schemas
- Key pattern documentation with examples
- Common query examples using AWS CLI
- Table relationship diagram

#### 4. Lambda Troubleshooting Component

Content includes:
- Error pattern catalog (timeout, permission, validation)
- CloudWatch Insights query templates
- Environment variable reference by Lambda
- Step-by-step investigation procedures

#### 5. Step Functions Troubleshooting Component

Content includes:
- 6-step workflow documentation
- Input/output schemas for each step
- Failure scenario matrix
- Retry and restart procedures

#### 6. ECS Service Troubleshooting Component

Content includes:
- Health check endpoint documentation
- GPU troubleshooting for NexusECSService
- Bedrock error handling for NexusStrandsAgentService
- Performance baseline tables

#### 7. Environment Configuration Component

Content includes:
- 3 environments with account IDs
- Configuration differences table
- Log access procedures
- Deployment health verification checklist

#### 8. Runbooks Component

Content includes:
- 5 detailed runbooks with symptoms, diagnosis, and resolution
- Decision trees for common issues
- Escalation triggers

#### 9. Monitoring & Alerting Component

Content includes:
- Alarm inventory with thresholds
- Key metrics by service type
- Escalation matrix
- Dashboard URLs

#### 10. Quick Reference Component

Content includes:
- Service endpoint table
- DynamoDB table names by environment
- Common CLI commands
- Contact information template

## Data Models

### Document Metadata

```yaml
title: Nexus Support Guide
version: 1.0
last_updated: YYYY-MM-DD
maintainer: Compliance Engineering Team
```

### Runbook Structure

Each runbook follows a consistent structure:

```markdown
### Runbook: [Issue Title]

**Symptoms:**
- Symptom 1
- Symptom 2

**Potential Causes:**
1. Cause A
2. Cause B

**Diagnosis Steps:**
1. Step 1
2. Step 2

**Resolution:**
- For Cause A: [resolution]
- For Cause B: [resolution]

**Escalation:**
- When to escalate
- Who to contact
```

### Error Code Structure

```markdown
| Code | HTTP Status | Meaning | Resolution |
|------|-------------|---------|------------|
| NOT_FOUND | 404 | Resource does not exist | Verify resource ID |
| VALIDATION_ERROR | 400 | Invalid request | Check request format |
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Since this is a documentation deliverable rather than a software implementation, traditional property-based testing does not apply. However, we can define documentation completeness properties:

**Documentation Completeness Properties:**

1. All acceptance criteria from requirements map to specific sections in the support guide
2. All packages listed in Package Architecture Guide appear in the support guide inventory
3. All DynamoDB tables documented in existing docs appear in the database reference
4. All API endpoints from Lambda handlers appear in the API reference
5. All environment variables from Lambda code appear in the configuration reference

These properties can be verified through manual review or automated document parsing.

## Error Handling

### Document Maintenance

The support guide should include:
- Version history section
- Last updated timestamp
- Process for submitting corrections
- Review schedule (quarterly recommended)

### Known Limitations

Document the following limitations:
- Information may become stale as system evolves
- Some procedures may require adjustment for specific scenarios
- Contact information requires periodic verification

## Testing Strategy

### Manual Review Checklist

Since this is a documentation deliverable, testing consists of manual review:

1. **Completeness Review**: Verify all requirements are addressed
2. **Accuracy Review**: Validate technical content against source code
3. **Usability Review**: Have a support engineer follow procedures
4. **Formatting Review**: Ensure consistent markdown formatting

### Validation Approach

| Requirement | Validation Method |
|-------------|-------------------|
| Architecture diagrams | Visual inspection, compare to source docs |
| API documentation | Compare to Lambda handler code |
| Database schemas | Compare to DynamoDB table definitions |
| Environment config | Compare to CDK stack |
| Runbooks | Dry-run procedures in test environment |

### Review Process

1. Author creates initial draft
2. Technical review by development team
3. Operational review by support team
4. Final approval by team lead
5. Publish to documentation repository
