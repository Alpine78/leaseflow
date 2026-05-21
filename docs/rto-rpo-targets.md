# Production RTO/RPO Targets

## Purpose

Define LeaseFlow's recovery targets for a future production-like stack.

This is a planning document. It does not implement disaster recovery
automation, change Terraform defaults, change RDS configuration, or prove that
the targets have been met.

## Targets

| Objective | Target | Meaning |
| --- | --- | --- |
| Recovery Time Objective (RTO) | 4 hours | Restore the application to usable service within 4 hours of declaring a production recovery event. |
| Recovery Point Objective (RPO) | 24 hours | Limit production database data loss to no more than 24 hours. |

These targets are intentionally modest. They fit a small SaaS or portfolio-grade
production-like posture where operator-driven restore is acceptable at first,
but recovery expectations still need to be explicit and testable before real
tenant data is stored.

## Rationale

- A 4-hour RTO gives enough room for an operator-run restore, application
  configuration review, migration validation, and browser/API smoke validation.
- A 24-hour RPO aligns with RDS automated backups and point-in-time restore as
  the first production-like recovery mechanism.
- The targets avoid implying high availability, multi-region failover, or
  automated disaster recovery that LeaseFlow does not currently implement.
- The targets are stricter than the current cost-aware dev posture, so they are
  production-like goals rather than claims about today's dev environment.

## Backup And Restore Expectations

Production-like RDS should keep at least `7` days of automated backups. This
supports the 24-hour RPO target with margin and gives operators a wider restore
window for validation and recovery.

Before production use, restore validation must prove:

- the latest restorable point is available within the expected RPO window
- a temporary restored DB can be created privately and encrypted
- application migrations and schema checks pass through a private path
- the application can be redeployed or reconfigured against the restored data
- the total recovery workflow can complete inside the 4-hour RTO target

## Validation Cadence

Run production-like restore validation:

- before storing real tenant data
- before any production go-live claim
- quarterly while a production-like environment exists
- after meaningful DB schema, RDS module, backup retention, migration workflow,
  or restore runbook changes

Evidence must record pass/fail status against the 4-hour RTO and 24-hour RPO,
but it must not include tenant data, tenant IDs, DB endpoints, secrets, SSM
values, JWTs, passwords, full connection strings, or row contents.

## Current Dev Boundary

The current dev stack remains cost-aware and destroyable:

- `db_backup_retention_period = 1`
- `db_deletion_protection = false`
- `db_skip_final_snapshot = true`

The dev restore validation runbook remains useful for proving the mechanics of
private RDS restore. It does not prove the production-like RTO/RPO targets until
the validation is timed and measured against the targets in this document.
