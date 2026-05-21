# RDS Production-Like Protection Baseline

## Purpose

Define the RDS protection posture LeaseFlow would need before storing real
tenant data or running a production-like environment.

The shared RDS Terraform module now exposes production-like protection inputs.
The current dev environment still defaults to a cost-controlled, destroyable
posture.

Not included in this baseline:

- AWS Backup plans.
- Cross-region replication.
- Public RDS access.
- Bastion hosts.
- Application or schema changes.

## Current Dev Posture

Default Terraform-managed dev RDS settings:

| Control | Current dev value | Reason |
| --- | --- | --- |
| Public access | `publicly_accessible = false` | RDS must stay private. |
| Storage encryption | `storage_encrypted = true` | Encrypt data at rest. |
| Backup retention | `backup_retention_period = 1` | Minimal dev restore window for cost control. |
| Multi-AZ | `multi_az = false` | Lower dev cost. |
| Deletion protection | `deletion_protection = false` | Allows easy dev stack destroy. |
| Final snapshot | `skip_final_snapshot = true` | Faster and cheaper dev cleanup. |

This posture is acceptable for short-lived portfolio/dev validation. It is not
production-ready database protection.

## Implemented Module Controls

The `rds_postgres` module accepts these protection inputs:

| Input | Dev default | Production-like expectation |
| --- | --- | --- |
| `backup_retention_period` | `1` | At least `7` when deletion protection is enabled. |
| `deletion_protection` | `false` | `true` for production-like data. |
| `skip_final_snapshot` | `true` | `false` when deletion protection is enabled. |
| `final_snapshot_identifier` | `null` | Required when final snapshots are enabled. |

The module keeps `publicly_accessible = false`, `storage_encrypted = true`, and
`multi_az = false` for the current low-cost dev shape.

The module validates these combinations:

- `backup_retention_period` must be at least `7` when
  `deletion_protection = true`.
- `deletion_protection = true` requires `skip_final_snapshot = false`.
- `skip_final_snapshot = false` requires a non-empty
  `final_snapshot_identifier`.

`lifecycle.prevent_destroy` is intentionally not variable-controlled in the
shared dev module. Terraform lifecycle meta-arguments require literal values, so
a future dedicated production environment can hardcode `prevent_destroy` without
breaking dev destroy workflows.

## Production-Like Baseline

Recovery targets are defined in `docs/rto-rpo-targets.md`: RTO 4 hours and RPO
24 hours. The baseline below is the minimum RDS posture expected to support
those targets at the planning level.

| Control | Production-like baseline | Cost impact | Why |
| --- | --- | --- | --- |
| Public access | Keep disabled. | None | Public RDS access is not an acceptable shortcut. |
| Backup retention | Minimum `7` days before real tenant or demo-critical data. | Low to medium | Gives a wider point-in-time restore window than dev. |
| Deletion protection | Enable by default. | None | Prevents accidental destructive deletes. |
| Final snapshot | Require before destructive deletion. | Medium | Preserves a last recovery point before removal. |
| Multi-AZ | Enable only when availability justifies the added cost. | Medium to high | Improves availability and failover posture. |
| Restore validation | Run before go-live and after meaningful DB changes. | Medium | Proves restore behavior, not just backup configuration. |
| Data-level validation | Use only a private execution path. | Low to medium | Confirms schema/data posture without exposing RDS. |

## Recovery Assumptions

These are project assumptions, not AWS service guarantees:

- Dev RTO: best effort, operator-driven, suitable only for learning and demo
  recovery.
- Dev RPO: bounded by the current one-day backup retention and latest
  restorable time.
- Production-like RTO: 4 hours.
- Production-like RPO: 24 hours.
- Backup retention must stay at least `7` days for production-like use so the
  24-hour RPO has restore-window margin.
- Restore validation evidence must be kept for production-like readiness claims.

## Decision Rules

Keep the current dev posture when:

- the environment is short-lived
- data can be recreated
- AWS cost control is more important than recovery realism
- the stack is destroyed after validation

Move to the production-like baseline when:

- real tenant data exists
- demo data is difficult or expensive to recreate
- multiple operators depend on the environment
- recovery expectations are explicit
- destructive changes require reviewable safeguards

## Restore Validation

Dev restore validation remains covered by:

- `docs/runbooks/dev-rds-restore-validation.md`
- `docs/runbooks/dev-rds-private-data-validation.md`

For production-like use, restore validation must include:

- source DB identifier
- latest restorable time
- restore start and completion time
- pass/fail against the 4-hour RTO and 24-hour RPO targets
- restored DB privacy and encryption posture
- migration/schema validation through a private path
- cleanup confirmation or documented reason for retention
- follow-up actions for any gap

Safe evidence must not include tenant data, tenant IDs, passwords, SSM values,
JWTs, full connection strings, or row contents.

## Well-Architected Notes

Reliability:

- Backup retention, final snapshots, and restore validation support recovery.
- Multi-AZ supports availability and failover, not backup retention.

Security:

- RDS remains private.
- Data-level restore checks must stay inside an approved private execution path.
- Evidence must exclude secrets and tenant data.

Cost Optimization:

- Longer retention, final snapshots, and Multi-AZ can increase cost.
- Production-like controls should be enabled only when their recovery or
  availability value is accepted.

Operational Excellence:

- Restore validation cadence and evidence make recoverability reviewable.
- Destructive database operations need explicit operator workflow.

## SAA-C03 Pitfalls

- Automated backups are not the same as restore validation.
- Backup retention defines the point-in-time restore window.
- Multi-AZ is not a backup feature.
- Deletion protection does not replace backups.
- A final snapshot is not the same as continuous point-in-time recovery.
- A private restored DB still needs a private validation path.
