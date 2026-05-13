mock_provider "aws" {}

variables {
  name_prefix           = "leaseflow-test"
  private_subnet_ids    = ["subnet-123", "subnet-456"]
  rds_security_group_id = "sg-123"
  db_name               = "leaseflow"
  db_username           = "leaseflow_admin"
  db_password           = "not-a-real-password"
}

run "defaults_preserve_dev_posture" {
  command = plan

  assert {
    condition     = aws_db_instance.this.backup_retention_period == 1
    error_message = "Default backup retention should remain 1 day for cost-aware dev."
  }

  assert {
    condition     = aws_db_instance.this.deletion_protection == false
    error_message = "Default deletion protection should remain disabled for dev destroy."
  }

  assert {
    condition     = aws_db_instance.this.skip_final_snapshot == true
    error_message = "Default final snapshot should remain skipped for dev destroy."
  }

  assert {
    condition     = aws_db_instance.this.final_snapshot_identifier == null
    error_message = "Default final snapshot identifier should be unset."
  }

  assert {
    condition     = aws_db_instance.this.publicly_accessible == false
    error_message = "RDS must remain private."
  }

  assert {
    condition     = aws_db_instance.this.storage_encrypted == true
    error_message = "RDS storage must remain encrypted."
  }

  assert {
    condition     = aws_db_instance.this.multi_az == false
    error_message = "Multi-AZ remains out of scope for this baseline."
  }
}

run "production_like_protection_inputs" {
  command = plan

  variables {
    backup_retention_period   = 7
    deletion_protection       = true
    skip_final_snapshot       = false
    final_snapshot_identifier = "leaseflow-prod-final-20260513"
  }

  assert {
    condition     = aws_db_instance.this.backup_retention_period == 7
    error_message = "Production-like backup retention should be configurable to 7 days."
  }

  assert {
    condition     = aws_db_instance.this.deletion_protection == true
    error_message = "Production-like deletion protection should be configurable."
  }

  assert {
    condition     = aws_db_instance.this.skip_final_snapshot == false
    error_message = "Production-like destroy should require a final snapshot."
  }

  assert {
    condition     = aws_db_instance.this.final_snapshot_identifier == "leaseflow-prod-final-20260513"
    error_message = "Production-like final snapshot identifier should be configurable."
  }
}

run "deletion_protection_requires_final_snapshot" {
  command = plan

  variables {
    backup_retention_period = 7
    deletion_protection     = true
    skip_final_snapshot     = true
  }

  expect_failures = [
    aws_db_instance.this,
  ]
}

run "final_snapshot_requires_identifier" {
  command = plan

  variables {
    skip_final_snapshot = false
  }

  expect_failures = [
    aws_db_instance.this,
  ]
}

run "deletion_protection_requires_seven_day_retention" {
  command = plan

  variables {
    backup_retention_period   = 1
    deletion_protection       = true
    skip_final_snapshot       = false
    final_snapshot_identifier = "leaseflow-prod-final-20260513"
  }

  expect_failures = [
    aws_db_instance.this,
  ]
}

run "backup_retention_must_be_at_least_one" {
  command = plan

  variables {
    backup_retention_period = 0
  }

  expect_failures = [
    aws_db_instance.this,
  ]
}
