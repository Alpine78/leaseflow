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
