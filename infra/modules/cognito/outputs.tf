output "user_pool_id" {
  value       = aws_cognito_user_pool.this.id
  description = "Cognito user pool ID."
}

output "user_pool_client_id" {
  value       = aws_cognito_user_pool_client.this.id
  description = "Cognito app client ID."
}

output "hosted_ui_base_url" {
  value       = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com"
  description = "Managed Cognito Hosted UI base URL."
}
