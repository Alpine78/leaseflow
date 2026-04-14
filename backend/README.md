# Backend

Python Lambda backend for LeaseFlow MVP.

## What is implemented

- Lambda entry point with lightweight routing.
- `GET /health`
- `GET /properties`
- `POST /properties`
- `PATCH /properties/{property_id}`
- `GET /leases`
- `POST /leases`
- `PATCH /leases/{lease_id}`
- `GET /lease-reminders/due-soon`
- `GET /notifications`
- `PATCH /notifications/{notification_id}/read`
- JWT claim extraction from Cognito ID tokens (`sub`, `custom:tenant_id`)
- Tenant-scoped property, lease, reminder, and notification access.
- Audit logging for property and lease write flows.
- Alembic migration setup and internal migration event support.
- Internal due-lease-reminder scan event support.
- Local invoke helper for selected handler paths.

## Local setup

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
```

## Local PostgreSQL in WSL

For everyday backend development, prefer a local PostgreSQL instance in WSL instead of keeping the AWS dev RDS instance running.

Why:

- avoids ongoing AWS cost during normal development
- keeps the AWS deployment target unchanged
- lets you run migrations and backend checks against a real PostgreSQL database locally

One simple WSL setup:

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres createuser -P leaseflow_admin
sudo -u postgres createdb -O leaseflow_admin leaseflow
```

Then create a local env file from the example and load it before running backend commands:

```bash
cp .env.local.example .env.local
set -a
source .env.local
set +a
```

If you are working from the repo root in WSL with the backend virtual environment activated, you can then use:

```bash
make migrate-local
make db-check-local
make test-local
make test-integration-local
make invoke-local-health
make invoke-local-list-properties
make invoke-local-list-due-lease-reminders
make invoke-local-scan-due-lease-reminders
make invoke-local-create-property
```

Alembic uses `DATABASE_URL`, so this is the equivalent manual migration command:

```bash
export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
python -m alembic upgrade head
```

This local database is for development data only. Do not copy production or tenant-sensitive data into WSL.

The local DB integration tests prove that `Database.create_property()` both writes the `properties` row plus the matching `audit_logs` row on the happy path and rolls the whole transaction back if audit logging fails. They are intentionally opt-in and run separately from the normal fast unit-test flow.

The local invoke helper calls the existing Lambda handler directly with API Gateway v2-style events. That keeps local testing close to the deployed Lambda shape without introducing a separate local web framework.

The helper currently covers health, property listing and creation, due lease reminder listing, notification read acknowledgement, and the internal reminder scan event. It does not cover every public route.

You can override the sample create command values from the repo root in WSL:

```bash
make invoke-local-create-property PROPERTY_NAME="Annex" PROPERTY_ADDRESS="Side Street 5"
```

## Useful commands

```bash
python -m ruff check src tests migrations
python -m ruff format src tests migrations
python -m pytest -q
python -m alembic upgrade head
```

## Environment variables

- `APP_ENV` (default: `dev`)
- `LOG_LEVEL` (default: `INFO`)
- `DB_HOST`
- `DB_PORT` (default: `5432`)
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD` (optional if using SSM parameter)
- `DB_PASSWORD_SSM_PARAM` (SecureString parameter name)
- `AWS_REGION` (used when resolving SSM values)
