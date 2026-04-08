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

output "private_service_endpoints_security_group_id" {
  value       = aws_security_group.private_service_endpoints.id
  description = "Security group ID for interface VPC endpoints."
}

output "ssm_vpc_endpoint_id" {
  value       = aws_vpc_endpoint.ssm.id
  description = "SSM interface VPC endpoint ID."
}

output "kms_vpc_endpoint_id" {
  value       = aws_vpc_endpoint.kms.id
  description = "KMS interface VPC endpoint ID."
}
