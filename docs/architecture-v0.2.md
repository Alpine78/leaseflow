# LeaseFlow Architecture v0.2

## Overview

LeaseFlow is a serverless, multi-tenant rental management MVP on AWS. The architecture emphasizes clear tenant boundaries, low operational overhead, and realistic production patterns.

## Architecture Diagram

![LeaseFlow architecture](diagrams/leaseflow-architecture.svg)

## Core Components

- **API Gateway (HTTP API)**: public HTTPS entry point.
- **Lambda (Python)**: backend request handling and domain logic.
- **Cognito**: authentication and JWT issuance.
- **RDS PostgreSQL (private)**: core relational data store.
- **CloudWatch**: application logs, baseline alarms, and operational visibility.
- **Terraform**: infrastructure provisioning and repeatability.
- **EventBridge Scheduler**: daily invocation of the internal reminder scan workflow.

## Multi-Tenant Design

- `tenant_id` is mandatory in tenant-owned domain tables.
- Backend extracts tenant context from Cognito JWT claim `custom:tenant_id`.
- Protected HTTP API calls use a Cognito ID token so the tenant custom attribute is available to the backend.
- Tenant context is never trusted from client-provided payload.
- Query patterns are tenant-scoped by design.

## Data and Persistence

- PostgreSQL is chosen over DynamoDB to keep relational queries and schema evolution straightforward for this MVP.
- Initial schema includes `properties` and `audit_logs`.
- Audit records are written for critical state changes (property creation).
- Reminder notifications are persisted in PostgreSQL before any future external delivery step.

## Security Baseline Alignment

- App-level tenant isolation with explicit auth checks.
- Cognito user pool stores tenant membership in custom attribute `custom:tenant_id`.
- Private RDS in VPC subnets, not publicly accessible.
- Least-privilege IAM for Lambda and API integration.
- Least-privilege IAM for EventBridge Scheduler to invoke the backend Lambda.
- Secrets via SSM Parameter Store SecureString, not hardcoded values.
- Private Lambda access to SSM and KMS uses interface VPC endpoints instead of a NAT path.
- Baseline CloudWatch alarms cover backend Lambda errors, Lambda throttles, HTTP API 5xx responses, and scheduler target failures.
- Structured JSON logging for traceability.

## Cost-Aware Decisions

- Single backend Lambda for MVP simplicity.
- One RDS instance in dev with small sizing.
- No NAT Gateway in dev environment.
- Private AWS API dependencies are reached through targeted interface endpoints where required.
- No extra services unless they deliver clear MVP value.
- One daily scheduler is preferred over per-tenant schedules to keep dev-stage operational cost and complexity low.

## Diagram Source

The version-controlled source for the architecture diagram lives in:

- `docs/diagrams/leaseflow-architecture.d2`

Render it locally after installing the D2 CLI:

```bash
cd docs/diagrams
d2 leaseflow-architecture.d2 leaseflow-architecture.svg
```
