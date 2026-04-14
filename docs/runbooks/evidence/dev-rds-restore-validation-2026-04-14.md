# Dev RDS Restore Validation Evidence - 2026-04-14

## Summary

The dev RDS restore validation runbook was executed successfully against the AWS dev environment.

Result:

- Source DB had automated backups enabled.
- A temporary private RDS instance was restored from the latest restorable point.
- The restored DB reached `available`.
- The restored DB remained private and encrypted.
- The temporary restored DB was deleted after validation.

## Context

- Date: 2026-04-14
- Region: `eu-north-1`
- Source DB: `leaseflow-dev-postgres`
- Restore DB: `leaseflow-dev-postgres-restore-20260414-0630`
- Runbook: `docs/runbooks/dev-rds-restore-validation.md`

The dev stack had been destroyed before this validation to avoid ongoing AWS cost, so it was recreated with Terraform before running the restore test.

Terraform apply result:

```text
Apply complete! Resources: 44 added, 0 changed, 0 destroyed.
```

## Source DB Backup Posture

Captured before restore:

```text
DBInstanceIdentifier: leaseflow-dev-postgres
Status:               available
BackupRetention:      1
LatestRestorableTime: 2026-04-14T06:20:05+00:00
PubliclyAccessible:   False
StorageEncrypted:     True
DBSubnetGroup:        leaseflow-dev-db-subnet-group
VpcSecurityGroupId:   sg-0f9c964ba30648df9
Engine:               postgres
EngineVersion:        15.17
InstanceClass:        db.t3.micro
```

Captured after restore cleanup:

```text
DBInstanceIdentifier: leaseflow-dev-postgres
Status:               available
BackupRetention:      1
LatestRestorableTime: 2026-04-14T06:39:30+00:00
PubliclyAccessible:   False
StorageEncrypted:     True
```

## Restore Execution

Restore target:

```text
RESTORE_DB=leaseflow-dev-postgres-restore-20260414-0630
RESTORE_START_UTC=2026-04-14T06:29:54Z
```

The restore was started with:

- source DB: `leaseflow-dev-postgres`
- target DB: `leaseflow-dev-postgres-restore-20260414-0630`
- `--use-latest-restorable-time`
- instance class: `db.t3.micro`
- DB subnet group: `leaseflow-dev-db-subnet-group`
- RDS security group: `sg-0f9c964ba30648df9`
- `--no-publicly-accessible`

Initial restore response confirmed:

```text
DBInstanceStatus:   creating
PubliclyAccessible: false
StorageEncrypted:   true
MultiAZ:            false
EngineVersion:      15.17
```

## Restore Completion

Waiter timing:

```text
WAIT_START_UTC=2026-04-14T06:30:20Z
WAIT_END_UTC=2026-04-14T06:38:25Z
```

Approximate restore wait duration: 8 minutes 5 seconds.

## Restored DB Posture

Captured after the restored DB reached `available`:

```text
DBInstanceIdentifier: leaseflow-dev-postgres-restore-20260414-0630
Status:               available
PubliclyAccessible:   False
StorageEncrypted:     True
DBSubnetGroup:        leaseflow-dev-db-subnet-group
VpcSecurityGroupId:   sg-0f9c964ba30648df9
Engine:               postgres
EngineVersion:        15.17
InstanceClass:        db.t3.micro
Endpoint:             leaseflow-dev-postgres-restore-20260414-0630.cbmk8q0s6lce.eu-north-1.rds.amazonaws.com
```

Validation outcome:

- Restored DB reached `available`.
- Restored DB stayed private.
- Restored DB stayed encrypted.
- Restored DB used the expected DB subnet group.
- Restored DB used the expected RDS security group.

## Cleanup Evidence

Delete timing:

```text
DELETE_START_UTC=2026-04-14T06:43:06Z
DELETE_END_UTC=2026-04-14T06:44:40Z
```

Delete response:

```text
leaseflow-dev-postgres-restore-20260414-0630 deleting False True
```

Final cleanup verification:

```text
DBInstanceNotFound: DBInstance leaseflow-dev-postgres-restore-20260414-0630 not found.
```

Cleanup outcome:

- Temporary restore DB was deleted.
- No final snapshot was kept for the temporary restore DB.
- Automated backups for the temporary restore DB were deleted.

## Out of Scope

Data-level SQL validation was not performed in this run.

Reason:

- The restored DB is private.
- The runbook intentionally avoids connecting from a public laptop.
- Private data-level validation is tracked separately in issue `#54`.

## Follow-Up

- Define a private data-level validation path for restored dev RDS.
- Document restore validation cadence and backup retention review.

## SAA-C03 Takeaway

This validates more than backup configuration. It demonstrates that automated RDS backups can be restored into a private encrypted DB instance and cleaned up after validation.
