output "user_pool_id" {
  value       = aws_cognito_user_pool.this.id
  description = "Cognito user pool ID."
}

output "user_pool_client_id" {
  value       = aws_cognito_user_pool_client.this.id
  description = "Cognito app client ID."
}
