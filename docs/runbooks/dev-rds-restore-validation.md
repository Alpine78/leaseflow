# Dev RDS Restore Validation Runbook

## Purpose

Validate that the Terraform-managed dev RDS PostgreSQL instance can be restored from automated backups without making the database public or adding permanent infrastructure.

This is an operator-run dev procedure, not an automated disaster recovery platform.

## Current Dev Assumptions

- Source DB instance: `leaseflow-dev-postgres`.
- Engine: Amazon RDS for PostgreSQL.
- Backup retention: `1` day in Terraform.
- Storage encryption: enabled.
- Public access: disabled.
- Multi-AZ: disabled for dev cost control.
- Final snapshot on destroy: disabled for dev cost control.

## Guardrails

- Run this only in dev.
- Keep the restored DB private.
- Use the same DB subnet group and RDS security group as the source DB.
- Do not import the temporary restore DB into Terraform state.
- Delete the restored DB after validation.
- Do not copy tenant data outside AWS.

## Preconditions

- AWS CLI is authenticated with the Terraform/dev account.
- `AWS_PROFILE=terraform` is set.
- Region is `eu-north-1`.
- The source DB status is `available`.
- The source DB has a non-empty `LatestRestorableTime`.

## Cadence and Retention Review

Restore validation cadence:

- Run this validation quarterly during MVP development.
- Rerun it after meaningful DB schema, RDS module, backup retention, or migration
  workflow changes.
- Rerun it before important portfolio or demo milestones when the dev database
  state matters.

Backup retention review triggers:

- Revisit `backup_retention_period` when dev data becomes difficult to recreate.
- Revisit it when demo data becomes important enough to justify a wider restore
  window.
- Revisit it before introducing a pre-prod or prod-like environment.
- Revisit it when recovery expectations exceed the current one-day dev restore
  window.

Current decision:

- Keep dev `backup_retention_period = 1` for cost control.
- Do not add Multi-AZ, cross-region replication, AWS Backup, or production DR
  automation in this dev runbook.
- Increase retention only when the recoverability benefit is explicitly accepted
  against the added storage cost.

## Step 1: Capture Source Backup Readiness

What it does: reads source RDS backup, networking, and encryption posture before restore.
Target service: Amazon RDS dev DB instance `leaseflow-dev-postgres`.

```bash
export AWS_PROFILE=terraform
export AWS_REGION=eu-north-1
export SOURCE_DB=leaseflow-dev-postgres

aws rds describe-db-instances \
  --db-instance-identifier "$SOURCE_DB" \
  --query 'DBInstances[0].{
    Status:DBInstanceStatus,
    BackupRetention:BackupRetentionPeriod,
    LatestRestorableTime:LatestRestorableTime,
    PubliclyAccessible:PubliclyAccessible,
    StorageEncrypted:StorageEncrypted,
    DBSubnetGroup:DBSubnetGroup.DBSubnetGroupName,
    VpcSecurityGroupIds:VpcSecurityGroups[].VpcSecurityGroupId
  }' \
  --output table
```

Expected evidence:

- `Status` is `available`.
- `BackupRetention` is `1`.
- `LatestRestorableTime` is populated.
- `PubliclyAccessible` is `False`.
- `StorageEncrypted` is `True`.

## Step 2: Restore a Temporary DB

What it does: restores the latest restorable point to a temporary private DB instance.
Target service: Amazon RDS restore target in dev.

```bash
export RESTORE_DB="leaseflow-dev-postgres-restore-$(date -u +%Y%m%d%H%M)"

export DB_SUBNET_GROUP=$(
  aws rds describe-db-instances \
    --db-instance-identifier "$SOURCE_DB" \
    --query 'DBInstances[0].DBSubnetGroup.DBSubnetGroupName' \
    --output text
)

export RDS_SG_IDS=$(
  aws rds describe-db-instances \
    --db-instance-identifier "$SOURCE_DB" \
    --query 'DBInstances[0].VpcSecurityGroups[].VpcSecurityGroupId' \
    --output text
)

aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier "$SOURCE_DB" \
  --target-db-instance-identifier "$RESTORE_DB" \
  --use-latest-restorable-time \
  --db-instance-class db.t3.micro \
  --db-subnet-group-name "$DB_SUBNET_GROUP" \
  --vpc-security-group-ids $RDS_SG_IDS \
  --no-publicly-accessible \
  --tags \
    Key=Project,Value=leaseflow \
    Key=Environment,Value=dev \
    Key=ManagedBy,Value=manual-runbook \
    Key=Purpose,Value=restore-validation
```

Expected evidence:

- The command returns a new DB instance identifier matching `$RESTORE_DB`.
- No public accessibility is requested.
- The restore uses the source DB subnet group and security group.

## Step 3: Wait for Restore Completion

What it does: waits until the temporary restored DB is available.
Target service: Amazon RDS restore target in dev.

```bash
aws rds wait db-instance-available \
  --db-instance-identifier "$RESTORE_DB"
```

Expected evidence:

- The waiter exits successfully.
- Restore duration is recorded for portfolio evidence.

## Step 4: Verify Restored DB Posture

What it does: confirms the restored DB is available, encrypted, and private.
Target service: Amazon RDS restore target in dev.

```bash
aws rds describe-db-instances \
  --db-instance-identifier "$RESTORE_DB" \
  --query 'DBInstances[0].{
    Status:DBInstanceStatus,
    Engine:Engine,
    EngineVersion:EngineVersion,
    PubliclyAccessible:PubliclyAccessible,
    StorageEncrypted:StorageEncrypted,
    DBSubnetGroup:DBSubnetGroup.DBSubnetGroupName,
    VpcSecurityGroupIds:VpcSecurityGroups[].VpcSecurityGroupId,
    Endpoint:Endpoint.Address
  }' \
  --output table
```

Expected evidence:

- `Status` is `available`.
- `PubliclyAccessible` is `False`.
- `StorageEncrypted` is `True`.
- DB subnet group and security group match the source DB.
- Endpoint exists, but it remains private.

Do not connect to the restored DB from a public laptop. Data-level validation
requires a controlled private execution path and is defined separately in
`docs/runbooks/dev-rds-private-data-validation.md`.

## Step 5: Clean Up

What it does: deletes the temporary restore DB and its automated backups.
Target service: Amazon RDS restore target in dev.

```bash
aws rds delete-db-instance \
  --db-instance-identifier "$RESTORE_DB" \
  --skip-final-snapshot \
  --delete-automated-backups

aws rds wait db-instance-deleted \
  --db-instance-identifier "$RESTORE_DB"
```

Expected evidence:

- Delete command is accepted.
- Waiter exits successfully.
- The temporary DB is no longer returned by `describe-db-instances`.

## Success Criteria

- Source DB has automated backups enabled.
- Temporary restore DB reaches `available`.
- Restored DB remains private and encrypted.
- Restore metadata is captured.
- Temporary restore DB is deleted after validation.

## Evidence to Capture

- Date, operator, and cadence trigger.
- Source DB identifier.
- `LatestRestorableTime`.
- Temporary restore DB identifier.
- Restore start and completion time.
- Source and restored DB posture output.
- Cleanup confirmation.
- Any errors and follow-up actions.

Keep one evidence note per successful validation run under
`docs/runbooks/evidence/`.

Do not capture tenant data values, secrets, JWTs, passwords, SSM parameter
values, or full connection strings.

## Cost Notes

- The restore creates a temporary RDS instance and storage.
- Delete it immediately after validation.
- Do not leave restore validation instances running overnight.
- Do not add Multi-AZ, cross-region replication, or AWS Backup plans in this dev runbook.
- A longer backup retention window can improve recoverability but may increase
  storage cost. Keep the dev default minimal unless the tradeoff is explicit.

## SAA-C03 Notes

- Automated backups and point-in-time restore are different from manual snapshots.
- A backup retention period of `0` disables automated backups.
- Backup retention defines the restore window.
- A private restored DB still needs correct subnet group and security group settings.
- Restore validation proves recoverability better than just enabling backups.

## References

- AWS Prescriptive Guidance: [Backup and recovery for Amazon RDS](https://docs.aws.amazon.com/prescriptive-guidance/latest/backup-recovery/rds.html).
- AWS CLI Command Reference: [`restore-db-instance-to-point-in-time`](https://docs.aws.amazon.com/cli/latest/reference/rds/restore-db-instance-to-point-in-time.html).
- AWS CLI Command Reference: [`delete-db-instance`](https://docs.aws.amazon.com/cli/latest/reference/rds/delete-db-instance.html).
