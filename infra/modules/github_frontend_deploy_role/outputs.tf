output "role_arn" {
  description = "ARN of the GitHub Actions frontend deploy role."
  value       = aws_iam_role.frontend_deploy.arn
}

output "role_name" {
  description = "Name of the GitHub Actions frontend deploy role."
  value       = aws_iam_role.frontend_deploy.name
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider."
  value       = aws_iam_openid_connect_provider.github.arn
}
