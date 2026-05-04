output "sender_identity_configured" {
  value       = length(aws_sesv2_email_identity.sender) > 0
  description = "Whether an SES sender identity is configured."
}

output "smtp_vpc_endpoint_enabled" {
  value       = length(aws_vpc_endpoint.ses_smtp) > 0
  description = "Whether the SES SMTP interface VPC endpoint is configured."
}

output "smtp_vpc_endpoint_id" {
  value       = try(aws_vpc_endpoint.ses_smtp[0].id, null)
  description = "SES SMTP interface VPC endpoint ID when enabled."
}

output "smtp_vpc_endpoint_security_group_id" {
  value       = try(aws_security_group.ses_smtp_vpce[0].id, null)
  description = "SES SMTP interface VPC endpoint security group ID when enabled."
}
