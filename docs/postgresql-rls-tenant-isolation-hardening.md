# PostgreSQL RLS Tenant Isolation Hardening Plan

## Purpose

This document defines a future PostgreSQL Row-Level Security hardening path for
LeaseFlow. RLS is defense in depth, not a replacement for the current
application-layer tenant isolation model.

The first incremental RLS policy is implemented for `audit_logs`. Additional
tenant-owned tables remain future rollout work.

## Current Tenant Isolation Model

LeaseFlow currently derives tenant context from validated Cognito JWT claims.
The browser must not provide trusted tenant context in request bodies or query
parameters.

Application code passes the resolved tenant ID into explicit SQL predicates for
tenant-owned reads and writes. Tenant-safe composite relationships already exist
for dependent tables, so tenant boundaries are encoded in both query patterns
and foreign key design.

RLS must preserve these rules:

- JWT-derived tenant context remains the source of truth.
- Application-layer tenant filters remain mandatory.
- Client-supplied `tenant_id` remains untrusted.
- RLS adds a database-enforced backstop if an application query is weakened.

## RLS Candidate Tables

Primary candidates:

- `audit_logs` (implemented first with FORCE RLS)
- `notification_email_deliveries`
- `notification_contacts`
- `notification_contact_suppressions`
- `notifications`
- `leases`
- `properties`

These tables are tenant-owned and include `tenant_id`. Existing tenant-safe
foreign keys and uniqueness constraints remain required. RLS must not be used
as a reason to remove tenant IDs, tenant-scoped indexes, tenant-scoped foreign
keys, or application-level authorization checks.

Tables without tenant-owned business rows, migration metadata, or infrastructure
state are not part of the first RLS scope.

## Tenant Context Strategy

Future backend DB access should set tenant context transaction-locally:

```sql
SET LOCAL app.tenant_id = '<jwt tenant>';
```

The setting must happen inside the same transaction as the tenant-scoped query
or write. Policies can then compare table `tenant_id` with
`current_setting('app.tenant_id', true)`.

Do not use session-level `SET`. Lambda execution environments are reused, and a
future connection pool could reuse sessions across requests. Session-level
tenant state creates a cross-request leakage risk.

The future application DB role must not have `BYPASSRLS`. A separate migration
or admin role may own schema changes, but that role must not be used for normal
API request handling.

The backend now has a transaction helper that sets this context for normal
tenant-scoped `Database` methods. RLS policies are still future work, so the
existing application-level tenant predicates remain mandatory.

## Internal Job Design

Internal reminder and email delivery jobs may still be invoked without an
explicit tenant ID. The backend now discovers candidate tenant IDs first and
then processes each tenant through the same transaction-local tenant context
used by normal tenant-scoped methods.

Current internal direction:

- discover candidate tenants through an explicit safe internal mechanism.
- process each tenant inside its own transaction.
- set `SET LOCAL app.tenant_id` before tenant-owned reads and writes.
- keep internal event payloads sanitized and avoid browser-triggered scan or
  delivery actions.

The discovery step still performs limited distinct-tenant lookup before RLS
policies exist. If future RLS policies also cover discovery inputs, this may
need a separate tenant registry or another explicitly justified discovery path.

Any privileged bypass path must be explicitly justified, tested, and kept out of
browser/API request handling.

## Migration And Rollback Order

Recommended implementation order:

1. Add a backend transaction helper that sets tenant context with `SET LOCAL`.
   Completed for normal tenant-scoped `Database` methods.
2. Adapt internal reminder and delivery jobs so they can run tenant by tenant.
   Completed for the existing reminder scan and email delivery preparation/list
   paths.
3. Add RLS policies for one low-risk table first, then expand table by table.
   `audit_logs` is the first implemented table.
4. Add regression tests that intentionally omit application tenant predicates
   and verify RLS blocks cross-tenant access.

Remaining table rollout order:

1. `notification_email_deliveries`
2. `notification_contacts`
3. `notification_contact_suppressions`
4. `notifications`
5. `leases`
6. `properties`

Rollback must be documented in each migration. A safe rollback should be able to
disable RLS policies without changing application request behavior, because the
application layer must still enforce tenant filters.

## Risks And Controls

- Pooled or reused DB sessions can leak tenant context if session-level settings
  are used. Use transaction-local `SET LOCAL` only.
- Tenant discovery still needs review when policies are added to the tables it
  reads.
- Missing tenant context should fail closed. Policies should not silently allow
  access when `app.tenant_id` is unset.
- Migration/admin roles must be separated from normal application runtime
  access before production-like RLS readiness is claimed. That role split is
  not implemented by the first `audit_logs` RLS migration.
- Local integration tests must cover both application filtering and database
  policy enforcement once RLS is implemented.

## Follow-Up Tickets

- Add RLS tenant context transaction helper.
- Adapt internal reminder and delivery jobs for RLS.
- Add PostgreSQL RLS policies for tenant-owned domain tables.
- Add RLS regression and migration smoke tests.
