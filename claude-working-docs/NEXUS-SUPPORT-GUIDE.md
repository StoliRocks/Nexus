# Nexus Support Guide

---

**Version:** 1.0  
**Last Updated:** December 4, 2025  
**Maintainer:** Compliance Engineering Team

---

## Table of Contents

1. [System Overview](#1-system-overview)
   - [1.1 Architecture Diagram](#11-architecture-diagram)
   - [1.2 Synchronous API Data Flow](#12-synchronous-api-data-flow)
   - [1.3 Async Mapping Pipeline Flow](#13-async-mapping-pipeline-flow)
   - [1.4 Package Inventory](#14-package-inventory)

2. [API Reference](#2-api-reference)
   - [2.1 Framework API Endpoints](#21-framework-api-endpoints)
   - [2.2 Control API Endpoints](#22-control-api-endpoints)
   - [2.3 Mapping API Endpoints](#23-mapping-api-endpoints)
   - [2.4 Error Codes Reference](#24-error-codes-reference)
   - [2.5 Key Format Patterns](#25-key-format-patterns)

3. [Database Reference](#3-database-reference)
   - [3.1 DynamoDB Table Schemas](#31-dynamodb-table-schemas)
   - [3.2 Example Queries for Troubleshooting](#32-example-queries-for-troubleshooting)
   - [3.3 Job Status Lifecycle](#33-job-status-lifecycle)
   - [3.4 Table Relationships](#34-table-relationships)

4. [Lambda Troubleshooting](#4-lambda-troubleshooting)
   - [4.1 Common Lambda Error Patterns](#41-common-lambda-error-patterns)
   - [4.2 CloudWatch Logs Query Patterns](#42-cloudwatch-logs-query-patterns)
   - [4.3 Environment Variables by Lambda](#43-environment-variables-by-lambda)
   - [4.4 Lambda Investigation Procedures](#44-lambda-investigation-procedures)

5. [Step Functions Troubleshooting](#5-step-functions-troubleshooting)
   - [5.1 Workflow Steps with Inputs/Outputs](#51-workflow-steps-with-inputsoutputs)
   - [5.2 Identifying Failed Executions](#52-identifying-failed-executions)
   - [5.3 Common Failure Scenarios](#53-common-failure-scenarios)
   - [5.4 Remediation Procedures](#54-remediation-procedures)

6. [ECS Service Troubleshooting](#6-ecs-service-troubleshooting)
   - [6.1 NexusECSService Health Checks](#61-nexusecsservice-health-checks)
   - [6.2 NexusStrandsAgentService Health Checks](#62-nexusstrandsagentservice-health-checks)
   - [6.3 GPU Troubleshooting Procedures](#63-gpu-troubleshooting-procedures)
   - [6.4 Bedrock/Claude Errors](#64-bedrockclaude-errors)
   - [6.5 Performance Baselines](#65-performance-baselines)

7. [Environment Configuration](#7-environment-configuration)
   - [7.1 Deployment Environments](#71-deployment-environments)
   - [7.2 Environment-Specific Configurations](#72-environment-specific-configurations)
   - [7.3 Log and Metrics Access](#73-log-and-metrics-access)
   - [7.4 Deployment Health Verification](#74-deployment-health-verification)

8. [Runbooks](#8-runbooks)
   - [8.1 Mapping Job Stuck in PENDING](#81-mapping-job-stuck-in-pending)
   - [8.2 ECS Service Not Responding](#82-ecs-service-not-responding)
   - [8.3 High Latency in Mapping Operations](#83-high-latency-in-mapping-operations)
   - [8.4 DynamoDB Throttling Errors](#84-dynamodb-throttling-errors)
   - [8.5 Bedrock Rate Limiting or Errors](#85-bedrock-rate-limiting-or-errors)

9. [Monitoring & Alerting](#9-monitoring--alerting)
   - [9.1 CloudWatch Alarms](#91-cloudwatch-alarms)
   - [9.2 Key Metrics by Service Type](#92-key-metrics-by-service-type)
   - [9.3 Escalation Procedures](#93-escalation-procedures)
   - [9.4 Dashboard Locations](#94-dashboard-locations)

10. [Quick Reference](#10-quick-reference)
    - [10.1 Service Endpoints Table](#101-service-endpoints-table)
    - [10.2 DynamoDB Table Names Reference](#102-dynamodb-table-names-reference)
    - [10.3 Common CLI Commands Reference](#103-common-cli-commands-reference)
    - [10.4 Contact Information](#104-contact-information)

---

## 1. System Overview

<!-- Content to be added in task 2 -->

---

## 2. API Reference

<!-- Content to be added in task 3 -->

---

## 3. Database Reference

<!-- Content to be added in task 4 -->

---

## 4. Lambda Troubleshooting

<!-- Content to be added in task 5 -->

---

## 5. Step Functions Troubleshooting

<!-- Content to be added in task 6 -->

---

## 6. ECS Service Troubleshooting

<!-- Content to be added in task 7 -->

---

## 7. Environment Configuration

<!-- Content to be added in task 8 -->

---

## 8. Runbooks

<!-- Content to be added in task 9 -->

---

## 9. Monitoring & Alerting

<!-- Content to be added in task 10 -->

---

## 10. Quick Reference

<!-- Content to be added in task 11 -->
