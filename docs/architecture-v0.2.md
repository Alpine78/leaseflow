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
- **SNS**: baseline alarm action topic for AWS-native alert fan-out.
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
- Current schema includes `properties`, `leases`, `notifications`, and `audit_logs`.
- `properties`, `leases`, and `notifications` are tenant-owned domain tables.
- `notifications` persists due-soon reminder records and uses nullable `read_at` for read acknowledgement.
- Audit records are written for critical property and lease state changes.
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
- Baseline alarms publish alarm-state changes to an SNS topic; dev can optionally add one email subscription that requires confirmation before delivery starts.
- Structured JSON logging for traceability.

## Cost-Aware Decisions

- Single backend Lambda for MVP simplicity.
- One RDS instance in dev with small sizing.
- Dev RDS remains cost-controlled; the production-like protection baseline is
  documented separately in `docs/rds-production-protection-baseline.md`.
- No NAT Gateway in dev environment.
- Private AWS API dependencies are reached through targeted interface endpoints where required.
- No extra services unless they deliver clear MVP value.
- One daily scheduler is preferred over per-tenant schedules to keep dev-stage operational cost and complexity low.

## Frontend Direction

- `demo-client` remains local demo/operator tooling and is separate from the
  real browser frontend.
- The real frontend direction is documented in
  `docs/frontend-mvp-strategy.md`.
- The chosen frontend direction is React + Vite + TypeScript, and the first
  browser slice now exists under `frontend/`.
- Dev Terraform now provides Cognito Hosted UI foundation through a managed
  domain and OAuth Authorization Code + PKCE-capable app client settings.
- Dev Terraform now provides allowlisted browser CORS on the HTTP API for
  approved frontend origins.
- The browser frontend slice covers sign-in, dashboard summaries,
  properties and leases list/create/update flows, due-soon reminder display,
  and notifications list/mark-read UI.
- Terraform now defines a private S3 + CloudFront hosting path for the static
  SPA.
- Hosted asset upload and browser smoke validation are operator-run release
  validation steps, not CI deployment automation.
- The dashboard is the authenticated browser app entry point.

## Operational Runbooks

- Presentation-friendly MVP demo flow is documented in `docs/portfolio-demo-flow.md`.
- Safe local demo-client usage and sanitized evidence capture are documented in
  `docs/runbooks/demo-client-safe-demo.md`.
- Deployed dev smoke validation is documented in `docs/runbooks/deployed-dev-smoke-test.md`.
- Dev RDS restore validation is documented in `docs/runbooks/dev-rds-restore-validation.md`.
- Production-like RDS protection expectations are documented in
  `docs/rds-production-protection-baseline.md`.
- Production-readiness hardening is scoped in `docs/production-readiness-hardening.md`.
- The restore validation runbook defines the quarterly MVP cadence, event-driven
  rerun triggers, evidence retention, and backup retention review triggers.

## Diagram Source

The version-controlled source for the architecture diagram lives in:

- `docs/diagrams/leaseflow-architecture.d2`

Render it locally after installing the D2 CLI:

```bash
cd docs/diagrams
d2 leaseflow-architecture.d2 leaseflow-architecture.svg
```
