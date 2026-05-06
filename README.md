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
- EventBridge Scheduler
- CloudWatch (logs and operations)
- SSM Parameter Store SecureString (secrets/config)

## Repository Structure

- `backend/`: Lambda backend code, tests, and Alembic migrations.
- `frontend/`: React + Vite + TypeScript browser frontend slice.
- `infra/`: Terraform modules and environment composition.
- `docs/`: MVP and architecture docs.

## Portfolio Demo

Use `docs/portfolio-demo-flow.md` for a short deployed MVP walkthrough suitable
for portfolio reviews or interviews.

For a local browser-based demo helper, run:

```bash
make demo-client
```

Then open `http://127.0.0.1:8765`. The demo client is local portfolio tooling,
not a hosted production frontend.

The real browser frontend direction is documented in
`docs/frontend-mvp-strategy.md`.

For the real browser frontend slice:

```bash
cd frontend
npm ci --ignore-scripts
npm run dev
```

## Current MVP Status

Implemented now:

- Backend Lambda with lightweight routing
- `GET /health`
- `POST /properties`
- `GET /properties`
- `POST /leases`
- `GET /leases`
- `PATCH /properties/{property_id}`
- `PATCH /leases/{lease_id}`
- `GET /lease-reminders/due-soon`
- `GET /notifications`
- `PATCH /notifications/{notification_id}/read`
- Internal due reminder scan flow that writes notification records idempotently
- Daily EventBridge Scheduler invocation for the internal reminder scan
- JWT claim extraction with tenant-aware request context
- Tenant-scoped PostgreSQL access
- Explicit `rent_due_day_of_month` on leases to prepare future reminder flows
- Notification persistence for due-soon rent reminders
- Tenant-scoped notification contacts and disabled-by-default internal SES SMTP
  delivery worker for persisted due reminder notifications
- Audit logging for property and lease writes
- Alembic migrations for property, lease, and notification tables
- Terraform modules for network, RDS, Cognito, Lambda, and API Gateway
- Local portfolio demo client for the deployed MVP flow
- Real browser frontend slice with Hosted UI auth, dashboard summaries,
  properties and leases list/create/update flows, due-soon reminders, and
  notifications mark-read UI with safe aggregate email delivery status
- Terraform-managed S3 + CloudFront hosting path for the frontend SPA

Planned next:

- Refine SES production-readiness guardrails and delivery operations
- Add more automated backend and tenant-isolation test coverage
- Refine operational setup for scheduled workflows and monitoring

## Local Backend Checks

```bash
make format
make lint
make test
```

For everyday backend and database development in WSL, use the local PostgreSQL
workflow in `backend/README.md` instead of keeping the AWS dev RDS instance
running.

Migration command:

```bash
make migrate
```

## Infrastructure Layout

- `infra/bootstrap/terraform_state`: S3 bucket for Terraform remote state.
- `infra/modules/`: reusable Terraform modules (`network`, `rds_postgres`, `cognito`, `lambda_backend`, `api_http`, `frontend_hosting`)
- `infra/environments/dev`: dev environment composition using the modules

Terraform commands:

```bash
make tf-fmt
cd infra/environments/dev
terraform init -backend-config=backend.hcl
terraform plan
```

Create `infra/environments/dev/backend.hcl` from the remote state bootstrap
output before running dev environment Terraform commands.
