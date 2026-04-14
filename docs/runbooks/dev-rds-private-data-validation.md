# Dev RDS Private Data-Level Validation Runbook

## Purpose

Define the safe data-level validation contract for a restored dev RDS PostgreSQL
instance without making the database public or adding permanent infrastructure.

This runbook defines what to validate and what evidence is safe to capture. It
does not create a bastion, SQL console, Lambda validator, or Terraform-managed
operational tool.

## Current Status

The repository already has a private Lambda migration path for the configured
dev database. That path is not a restored-DB validation path because the Lambda
uses its deployed database configuration and does not accept an arbitrary
restored RDS endpoint.

Use this runbook only when an approved private execution path exists for the
temporary restored DB.

Approved private execution paths must meet all of these conditions:

- Run inside the AWS dev account and private network path that can reach RDS.
- Keep the restored DB `PubliclyAccessible=false`.
- Avoid public laptop-to-RDS connectivity.
- Avoid permanent bastion infrastructure unless a separate ticket approves it.
- Resolve database credentials without printing secrets or full connection
  strings.
- Run only read-only SQL checks.

## Guardrails

- Run this only in dev.
- Do not make the source or restored RDS instance public.
- Do not copy tenant data outside AWS.
- Do not select names, addresses, emails, messages, tenant IDs, JWTs, passwords,
  or connection strings.
- Capture row counts only, not row contents.
- Delete the temporary restored DB after validation and evidence capture.

## Preconditions

- `docs/runbooks/dev-rds-restore-validation.md` has restored a temporary DB.
- The restored DB is `available`, private, and encrypted.
- The operator has an approved private execution path to the restored endpoint.
- The execution path has read-only intent and uses the dev DB credentials.
- The expected Alembic head for this ticket is `20260409_0006`.

## Step 1: Capture Target Metadata

What it does: records the restored DB identifier and private endpoint without
connecting to the database from a public machine.
Target service: Amazon RDS restore target in dev.

```bash
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1
export RESTORE_DB=<temporary-restore-db-identifier>

aws rds describe-db-instances \
  --db-instance-identifier "$RESTORE_DB" \
  --query 'DBInstances[0].{
    DBInstanceIdentifier:DBInstanceIdentifier,
    Status:DBInstanceStatus,
    PubliclyAccessible:PubliclyAccessible,
    StorageEncrypted:StorageEncrypted,
    Endpoint:Endpoint.Address
  }' \
  --output table
```

Expected evidence:

- `Status` is `available`.
- `PubliclyAccessible` is `False`.
- `StorageEncrypted` is `True`.
- Endpoint hostname is captured, but no credentials are captured.

## Step 2: Run Read-Only SQL Checks Privately

What it does: validates schema presence, migration state, tenant-scoped columns,
and table row counts without reading tenant data values.
Target service: restored private Amazon RDS PostgreSQL database.

Run the SQL below only from the approved private execution path. The session
must be read-only.

```sql
BEGIN READ ONLY;

SELECT version_num
FROM alembic_version;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'alembic_version',
    'properties',
    'audit_logs',
    'leases',
    'notifications'
  )
ORDER BY table_name;

SELECT table_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name = 'tenant_id'
  AND table_name IN (
    'properties',
    'audit_logs',
    'leases',
    'notifications'
  )
ORDER BY table_name;

SELECT 'properties' AS table_name, count(*) AS row_count FROM properties
UNION ALL
SELECT 'audit_logs' AS table_name, count(*) AS row_count FROM audit_logs
UNION ALL
SELECT 'leases' AS table_name, count(*) AS row_count FROM leases
UNION ALL
SELECT 'notifications' AS table_name, count(*) AS row_count FROM notifications
ORDER BY table_name;

ROLLBACK;
```

Expected evidence:

- `version_num` is `20260409_0006`.
- Expected tables are present:
  - `alembic_version`
  - `audit_logs`
  - `leases`
  - `notifications`
  - `properties`
- `tenant_id` exists on:
  - `audit_logs`
  - `leases`
  - `notifications`
  - `properties`
- Row counts are captured only as aggregate counts.

## Step 3: Record Safe Evidence

What it does: defines the allowed evidence for portfolio and operational review.
Target service: restore validation evidence document.

Safe evidence:

- Date and operator.
- Source DB identifier.
- Temporary restore DB identifier.
- Restored DB endpoint hostname.
- Private execution path name, not credentials.
- Migration revision.
- Expected table presence.
- Tenant-scoped column presence.
- Aggregate row counts.

Forbidden evidence:

- Tenant IDs.
- Property names or addresses.
- Resident names.
- Notification titles or messages.
- Email addresses.
- JWTs or Cognito tokens.
- Passwords, SSM parameter values, or full connection strings.

## Success Criteria

- Data-level validation runs only through an approved private path.
- Restored DB stays private and encrypted.
- Alembic revision matches the expected head.
- Expected domain tables exist.
- Tenant-scoped tables include `tenant_id`.
- Evidence contains no tenant data values or secrets.

## Follow-Up

If repeated data-level validation is needed, add a separate ticket for a small
internal read-only Lambda validator. That implementation must accept a restored
DB endpoint explicitly, run only allow-listed SQL checks, avoid logging secrets,
and be removable or disabled after the validation run.

## SAA-C03 Notes

- RDS automated backups prove only that restore data exists; they do not prove
  the application schema is usable after restore.
- A private restored DB still requires a private execution path for SQL checks.
- Do not solve this by making RDS public; that weakens the security posture.
