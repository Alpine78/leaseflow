# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LeaseFlow is a serverless, multi-tenant rental management MVP on AWS. It is a learning/portfolio project — prefer small, reviewable changes and explain reasoning before making large edits. Do not expand scope beyond what is asked.

## Commands

### Backend (run from repo root)

```bash
make format          # ruff format
make lint            # ruff check
make test            # pytest (unit tests, no DB required)
```

Run a single test file:
```bash
cd backend && python -m pytest tests/test_properties_route.py -q
```

Local PostgreSQL workflow (requires WSL and `backend/.env.local`):
```bash
make migrate-local              # apply Alembic migrations to local DB
make test-local                 # pytest with local DB env loaded
make test-integration-local     # DB integration tests (LEASEFLOW_RUN_DB_INTEGRATION=1)
make invoke-local-health        # invoke handler locally
make invoke-local-list-properties
make invoke-local-create-property PROPERTY_NAME="X" PROPERTY_ADDRESS="Y"
```

Backend venv setup (WSL):
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Frontend (run from `frontend/`)

```bash
npm ci --ignore-scripts   # install (scripts disabled by .npmrc)
npm run dev               # Vite dev server at http://localhost:5173
npm run lint
npm run test
npm run build
npm audit --audit-level=high
```

Frontend env: copy `frontend/.env.example` to `frontend/.env.local` and fill from Terraform outputs (`VITE_API_BASE_URL`, `VITE_COGNITO_HOSTED_UI_BASE_URL`, `VITE_COGNITO_CLIENT_ID`). Restart Vite after changes.

### Infrastructure

```bash
make tf-fmt                             # terraform fmt -recursive
cd infra/environments/dev
terraform init -backend-config=backend.hcl
terraform plan
```

Requires `infra/environments/dev/backend.hcl` from the remote state bootstrap output.

## Architecture

### Backend

**Entry point**: `backend/src/app/handler.py` — a single Lambda function with manual routing. Routes are matched by HTTP method and path regex. Internal EventBridge events are distinguished by `event["source"] == "leaseflow.internal"` + `event["detail-type"]`.

**Database**: `backend/src/app/db.py` — a `Database` class encapsulating all SQL. All tenant-scoped queries go through `_tenant_transaction(tenant_id)`, which opens a psycopg connection, starts a transaction, and sets the `app.tenant_id` PostgreSQL config parameter before yielding. Every domain write also commits an `audit_logs` row in the same transaction.

**Auth**: `backend/src/app/auth.py` — `extract_auth_context(event)` reads `sub` and `custom:tenant_id` from the API Gateway JWT authorizer claims. `tenant_id` must always come from these JWT claims, never from the request body.

**Config**: `backend/src/app/config.py` — `load_settings()` (cached with `@lru_cache`) reads env vars; DB password and email SMTP credentials are resolved from SSM Parameter Store SecureString at runtime.

**Models**: `backend/src/app/models.py` — plain `@dataclass(slots=True)` value objects. No ORM.

**Migrations**: `backend/migrations/versions/` — Alembic, named `YYYYMMDD_NNNN_description.py`. Apply with `make migrate-local` (local) or `make migrate` (AWS).

**DB schema tables**: `properties`, `leases`, `notifications`, `notification_contacts`, `notification_contact_suppressions`, `notification_email_deliveries`, `audit_logs`. All tenant-owned tables have `tenant_id`.

**Internal flows**:
- Daily EventBridge Scheduler → Lambda with `detail-type: scan_due_lease_reminders` → writes `notifications` records idempotently.
- `deliver_notification_emails` internal event → SES SMTP delivery (disabled by default; requires `NOTIFICATION_EMAIL_DELIVERY_ENABLED=true`).
- SES bounce/complaint events → EventBridge → Lambda → suppression records.

### Frontend

**Stack**: React + React Router + TypeScript + Vite. No Redux or external state library.

**Auth**: Cognito Hosted UI with OAuth Authorization Code + PKCE. `AuthContext` (`frontend/src/app/AuthContext.tsx`) manages session state from `sessionStorage`. Protected routes use `ProtectedRoute`. API calls use the `id_token` (not `access_token`) because the backend needs the `custom:tenant_id` custom claim.

**Feature pattern**: each page has a matching custom hook in `frontend/src/features/<domain>/use<Domain>Page.ts` that handles API calls and local state. Page components stay thin.

**API client**: `frontend/src/lib/api.ts` — typed fetch wrappers for all backend routes.

**Routing**: `frontend/src/app/App.tsx` — React Router routes. All non-landing routes are wrapped in `ProtectedRoute` + `AppShell`.

**Hosted deploy**: S3 + CloudFront. Rebuild and re-upload whenever any `VITE_*` env value changes (values are embedded at build time). CI deploy via `.github/workflows/deploy-frontend-dev.yml` using GitHub OIDC.

### Infrastructure

Terraform modules in `infra/modules/`: `network`, `rds_postgres`, `cognito`, `lambda_backend`, `api_http`, `frontend_hosting`, `cloudwatch_alarms`, `reminder_scheduler`, `ses_email_foundation`, `ses_feedback_eventbridge_processor`, `github_frontend_deploy_role`, `cost_controls`.

Dev environment composition: `infra/environments/dev/`. Remote state in S3, bootstrapped from `infra/bootstrap/terraform_state`.

## Critical Constraints

- **Tenant isolation is mandatory**: every tenant-scoped query must filter by `tenant_id`. Never trust `tenant_id` from request bodies — derive it from JWT claims only.
- **Parameterized SQL only**: no string-built queries.
- **Audit logging**: domain writes (property, lease, notification contact) must commit audit records in the same transaction.
- **RDS is private**: never publicly accessible; accessed from Lambda via VPC.
- **No NAT Gateway in dev**: private AWS API access uses VPC interface endpoints.
- **Cost-aware**: avoid adding AWS services without clear MVP justification.
- **DB integration tests are opt-in**: gated by `LEASEFLOW_RUN_DB_INTEGRATION=1`, run separately from the normal fast unit-test flow.

## Key Files

- `AGENTS.md` — working style and hallucination prevention rules (apply these in this repo)
- `docs/architecture-v0.2.md` — architecture diagram and design decisions
- `docs/security-baseline.md` — security requirements
- `backend/.env.local.example` — local DB config template
- `frontend/.env.example` — frontend env template
