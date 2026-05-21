output "endpoint" {
  value       = aws_db_instance.this.address
  description = "RDS endpoint hostname."
}

output "port" {
  value       = aws_db_instance.this.port
  description = "RDS port."
}

output "db_name" {
  value       = aws_db_instance.this.db_name
  description = "Database name."
}

output "backup_retention_period" {
  value       = aws_db_instance.this.backup_retention_period
  description = "Configured RDS automated backup retention period in days."
}

output "deletion_protection" {
  value       = aws_db_instance.this.deletion_protection
  description = "Whether RDS deletion protection is enabled."
}

output "skip_final_snapshot" {
  value       = aws_db_instance.this.skip_final_snapshot
  description = "Whether RDS final snapshot creation is skipped on destroy."
}

output "master_user_secret_arn" {
  value       = try(aws_db_instance.this.master_user_secret[0].secret_arn, "")
  description = "ARN of the Secrets Manager secret for the RDS master user password."
}
