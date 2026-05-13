resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, { Name = "${var.name_prefix}-db-subnet-group" })
}

resource "aws_db_instance" "this" {
  identifier = "${var.name_prefix}-postgres"

  engine                = "postgres"
  engine_version        = var.engine_version
  instance_class        = var.instance_class
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.allocated_storage + 20
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.rds_security_group_id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period   = var.backup_retention_period
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.final_snapshot_identifier
  deletion_protection       = var.deletion_protection
  apply_immediately         = true

  lifecycle {
    precondition {
      condition     = var.backup_retention_period >= 1
      error_message = "backup_retention_period must be at least 1."
    }

    precondition {
      condition     = !var.deletion_protection || var.backup_retention_period >= 7
      error_message = "deletion_protection requires backup_retention_period to be at least 7."
    }

    precondition {
      condition     = var.skip_final_snapshot || try(length(trimspace(var.final_snapshot_identifier)), 0) > 0
      error_message = "final_snapshot_identifier is required when skip_final_snapshot is false."
    }

    precondition {
      condition     = !var.deletion_protection || !var.skip_final_snapshot
      error_message = "deletion_protection requires skip_final_snapshot to be false."
    }
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-postgres" })
}
