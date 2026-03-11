output "vpc_id" {
  value       = aws_vpc.this.id
  description = "VPC ID."
}

output "private_subnet_ids" {
  value       = aws_subnet.private[*].id
  description = "Private subnet IDs."
}

output "lambda_security_group_id" {
  value       = aws_security_group.lambda.id
  description = "Lambda SG ID."
}

output "rds_security_group_id" {
  value       = aws_security_group.rds.id
  description = "RDS SG ID."
}
