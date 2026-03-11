# Backend

Python Lambda backend for LeaseFlow MVP.

## What is implemented

- Lambda entry point with lightweight routing.
- `GET /health`
- `POST /properties`
- `GET /properties`
- JWT claim extraction (`sub`, `custom:tenant_id`)
- Tenant-scoped data access
- Audit logging on property creation
- Alembic migration setup

## Local setup

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
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
