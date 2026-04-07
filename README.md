# LeaseFlow

LeaseFlow is a cloud-native, multi-tenant rental management system MVP built as an AWS architecture and backend portfolio project.

## Goals

- Demonstrate practical AWS architecture decisions for a real MVP.
- Use Terraform for Infrastructure as Code.
- Build a production-relevant Python backend on Lambda.
- Apply security-by-design and tenant isolation from the first version.
- Keep development costs low.

## Core AWS Services

- API Gateway (HTTP API)
- Lambda (Python)
- Cognito (JWT auth)
- RDS PostgreSQL (private)
- EventBridge / Scheduler (planned next phase)
- CloudWatch (logs and operations)
- SSM Parameter Store SecureString (secrets/config)

## Repository Structure

- `backend/`: Lambda backend code, tests, and Alembic migrations.
- `infra/`: Terraform modules and environment composition.
- `docs/`: MVP and architecture docs.

## Current MVP Status

Implemented now:

- Backend Lambda with lightweight routing
- `GET /health`
- `POST /properties`
- `GET /properties`
- `POST /leases`
- `GET /leases`
- JWT claim extraction with tenant-aware request context
- Tenant-scoped PostgreSQL access
- Explicit `rent_due_day_of_month` on leases to prepare future reminder flows
- Audit logging for property and lease creation
- Alembic migrations for initial property and lease tables
- Terraform modules for network, RDS, Cognito, Lambda, and API Gateway

Planned next:

- Prepare reminder and scheduled workflow support on top of leases
- Add more automated backend and tenant-isolation test coverage
- Refine operational setup for scheduled workflows and monitoring

## Local Backend Checks

```bash
make format
make lint
make test
```

Migration command:

```bash
make migrate
```

## Infrastructure Layout

- `infra/modules/`: reusable Terraform modules (`network`, `rds_postgres`, `cognito`, `lambda_backend`, `api_http`)
- `infra/environments/dev`: dev environment composition using the modules

Terraform commands:

```bash
make tf-fmt
cd infra/environments/dev && terraform init && terraform plan
```
