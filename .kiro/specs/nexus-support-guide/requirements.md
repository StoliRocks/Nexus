# Requirements Document

## Introduction

This document defines the requirements for a comprehensive Nexus Support Guide. Nexus is an AWS compliance control mapping system that automatically maps AWS service controls to industry compliance frameworks (NIST SP 800-53, SOC2, PCI-DSS, HIPAA, ISO 27001, etc.). The support guide will serve as a troubleshooting and operational reference for engineers supporting the Nexus platform.

## Glossary

- **Nexus**: AWS compliance control mapping system using ML and LLM agents
- **Control**: A compliance requirement from a framework (e.g., NIST AC-1)
- **Framework**: A compliance standard (e.g., NIST SP 800-53, SOC2, PCI-DSS)
- **Mapping**: A relationship between a source control and target control with similarity scores
- **Enrichment**: LLM-generated expansion of control text with compliance context
- **Reasoning**: Human-readable rationale explaining why controls map together
- **NexusECSService**: GPU ML inference service for embeddings and reranking
- **NexusStrandsAgentService**: Claude-based agent service for enrichment and reasoning
- **Step Functions**: AWS orchestration service managing the async mapping workflow
- **frameworkKey**: Composite key format `frameworkName#version`
- **controlKey**: Composite key format `frameworkKey#controlId`
- **mappingKey**: Composite key format `controlKey1|controlKey2`

## Requirements

### Requirement 1

**User Story:** As a support engineer, I want a system architecture overview, so that I can understand how Nexus components interact and identify failure points.

#### Acceptance Criteria

1. THE Support Guide SHALL include a high-level architecture diagram showing all Nexus components and their relationships
2. THE Support Guide SHALL document the data flow for synchronous API operations (Framework, Control, Mapping CRUD)
3. THE Support Guide SHALL document the async mapping pipeline flow through Step Functions
4. THE Support Guide SHALL list all packages with their type (Lambda, ECS, Library) and purpose

### Requirement 2

**User Story:** As a support engineer, I want API endpoint documentation, so that I can verify correct API behavior and troubleshoot client issues.

#### Acceptance Criteria

1. THE Support Guide SHALL document all Framework API endpoints with HTTP methods, paths, and expected responses
2. THE Support Guide SHALL document all Control API endpoints with HTTP methods, paths, and expected responses
3. THE Support Guide SHALL document all Mapping API endpoints with HTTP methods, paths, and expected responses
4. THE Support Guide SHALL include common API error codes and their meanings
5. THE Support Guide SHALL document the key format patterns (frameworkKey, controlKey, mappingKey)

### Requirement 3

**User Story:** As a support engineer, I want DynamoDB table documentation, so that I can query data directly when debugging issues.

#### Acceptance Criteria

1. THE Support Guide SHALL document all DynamoDB tables with their primary keys and sort keys
2. THE Support Guide SHALL include example queries for common troubleshooting scenarios
3. THE Support Guide SHALL document the job status lifecycle (PENDING, RUNNING, COMPLETED, FAILED)
4. THE Support Guide SHALL explain the relationship between tables (Frameworks, Controls, Mappings, Jobs)

### Requirement 4

**User Story:** As a support engineer, I want Lambda troubleshooting procedures, so that I can diagnose and resolve Lambda-related failures.

#### Acceptance Criteria

1. THE Support Guide SHALL document common Lambda error patterns and their root causes
2. THE Support Guide SHALL include CloudWatch Logs query patterns for each Lambda type
3. THE Support Guide SHALL document environment variables required by each Lambda
4. THE Support Guide SHALL provide step-by-step procedures for investigating Lambda timeouts and errors

### Requirement 5

**User Story:** As a support engineer, I want Step Functions troubleshooting procedures, so that I can diagnose async mapping workflow failures.

#### Acceptance Criteria

1. THE Support Guide SHALL document each step in the mapping workflow with expected inputs and outputs
2. THE Support Guide SHALL include procedures for identifying failed Step Functions executions
3. THE Support Guide SHALL document common failure scenarios at each workflow step
4. THE Support Guide SHALL provide remediation steps for restarting or retrying failed workflows

### Requirement 6

**User Story:** As a support engineer, I want ECS service troubleshooting procedures, so that I can diagnose ML inference and agent service issues.

#### Acceptance Criteria

1. THE Support Guide SHALL document NexusECSService health check endpoints and expected responses
2. THE Support Guide SHALL document NexusStrandsAgentService health check endpoints and expected responses
3. THE Support Guide SHALL include procedures for diagnosing GPU-related issues in NexusECSService
4. THE Support Guide SHALL document common Bedrock/Claude errors in NexusStrandsAgentService
5. THE Support Guide SHALL include performance baselines for each ECS service endpoint

### Requirement 7

**User Story:** As a support engineer, I want environment-specific configuration documentation, so that I can verify correct deployment across stages.

#### Acceptance Criteria

1. THE Support Guide SHALL document all deployment environments (Beta, Gamma, Prod) with AWS account IDs
2. THE Support Guide SHALL list environment-specific configuration differences
3. THE Support Guide SHALL document how to access logs and metrics for each environment
4. THE Support Guide SHALL include procedures for verifying deployment health

### Requirement 8

**User Story:** As a support engineer, I want common issue runbooks, so that I can quickly resolve known problems.

#### Acceptance Criteria

1. THE Support Guide SHALL include a runbook for "Mapping job stuck in PENDING status"
2. THE Support Guide SHALL include a runbook for "ECS service not responding"
3. THE Support Guide SHALL include a runbook for "High latency in mapping operations"
4. THE Support Guide SHALL include a runbook for "DynamoDB throttling errors"
5. THE Support Guide SHALL include a runbook for "Bedrock rate limiting or errors"

### Requirement 9

**User Story:** As a support engineer, I want monitoring and alerting documentation, so that I can proactively identify and respond to issues.

#### Acceptance Criteria

1. THE Support Guide SHALL document CloudWatch alarms configured for Nexus components
2. THE Support Guide SHALL include key metrics to monitor for each service type
3. THE Support Guide SHALL document escalation procedures for critical alerts
4. THE Support Guide SHALL include dashboard locations for operational visibility

### Requirement 10

**User Story:** As a support engineer, I want a quick reference section, so that I can rapidly look up common information during incidents.

#### Acceptance Criteria

1. THE Support Guide SHALL include a quick reference table of all service endpoints
2. THE Support Guide SHALL include a quick reference for DynamoDB table names by environment
3. THE Support Guide SHALL include a quick reference for common CLI commands
4. THE Support Guide SHALL include contact information for escalation paths
