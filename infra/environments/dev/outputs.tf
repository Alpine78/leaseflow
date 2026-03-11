output "api_stage_invoke_url" {
  description = "API stage invoke URL."
  value       = module.api_http.stage_invoke_url
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID."
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito user pool app client ID."
  value       = module.cognito.user_pool_client_id
}

output "rds_endpoint" {
  description = "RDS endpoint."
  value       = module.rds_postgres.endpoint
}
