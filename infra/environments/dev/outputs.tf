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

output "cognito_hosted_ui_base_url" {
  description = "Managed Cognito Hosted UI base URL for the dev frontend auth flow."
  value       = module.cognito.hosted_ui_base_url
}

output "frontend_bucket_name" {
  description = "S3 bucket name for hosted frontend assets."
  value       = module.frontend_hosting.bucket_name
}

output "frontend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for the hosted frontend."
  value       = module.frontend_hosting.cloudfront_distribution_id
}

output "frontend_cloudfront_domain_name" {
  description = "CloudFront distribution domain name for the hosted frontend."
  value       = module.frontend_hosting.cloudfront_domain_name
}

output "frontend_cloudfront_url" {
  description = "CloudFront HTTPS URL for the hosted frontend."
  value       = module.frontend_hosting.cloudfront_url
}

output "rds_endpoint" {
  description = "RDS endpoint."
  value       = module.rds_postgres.endpoint
}

output "reminder_scan_schedule_name" {
  description = "Reminder scan schedule name."
  value       = module.reminder_scheduler.schedule_name
}

output "reminder_scan_schedule_arn" {
  description = "Reminder scan schedule ARN."
  value       = module.reminder_scheduler.schedule_arn
}

output "baseline_alarm_names" {
  description = "Baseline CloudWatch alarm names for the dev stack."
  value = compact([
    module.cloudwatch_alarms.lambda_errors_alarm_name,
    module.cloudwatch_alarms.lambda_throttles_alarm_name,
    module.cloudwatch_alarms.api_gateway_5xx_alarm_name,
    module.cloudwatch_alarms.scheduler_target_errors_alarm_name
  ])
}

output "baseline_alarm_notification_topic_name" {
  description = "SNS topic name used as the baseline CloudWatch alarm action target."
  value       = aws_sns_topic.baseline_alarm_notifications.name
}

output "baseline_alarm_notification_topic_arn" {
  description = "SNS topic ARN used as the baseline CloudWatch alarm action target."
  value       = aws_sns_topic.baseline_alarm_notifications.arn
}

output "baseline_alarm_email_subscription_configured" {
  description = "Whether a dev baseline alarm email subscription is configured."
  value       = length(aws_sns_topic_subscription.baseline_alarm_email) > 0
}

output "ses_sender_identity_configured" {
  description = "Whether an optional SES sender identity is configured for future dev email delivery validation."
  value       = module.ses_email_foundation.sender_identity_configured
}

output "ses_smtp_vpc_endpoint_enabled" {
  description = "Whether the optional SES SMTP interface VPC endpoint is configured."
  value       = module.ses_email_foundation.smtp_vpc_endpoint_enabled
}

output "ses_smtp_vpc_endpoint_id" {
  description = "SES SMTP interface VPC endpoint ID when enabled."
  value       = module.ses_email_foundation.smtp_vpc_endpoint_id
}

output "ses_smtp_vpc_endpoint_security_group_id" {
  description = "SES SMTP interface VPC endpoint security group ID when enabled."
  value       = module.ses_email_foundation.smtp_vpc_endpoint_security_group_id
}
