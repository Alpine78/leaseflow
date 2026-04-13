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
