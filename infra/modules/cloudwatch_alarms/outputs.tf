output "lambda_errors_alarm_name" {
  description = "Lambda errors alarm name."
  value       = aws_cloudwatch_metric_alarm.lambda_errors.alarm_name
}

output "lambda_errors_alarm_arn" {
  description = "Lambda errors alarm ARN."
  value       = aws_cloudwatch_metric_alarm.lambda_errors.arn
}

output "lambda_throttles_alarm_name" {
  description = "Lambda throttles alarm name."
  value       = aws_cloudwatch_metric_alarm.lambda_throttles.alarm_name
}

output "lambda_throttles_alarm_arn" {
  description = "Lambda throttles alarm ARN."
  value       = aws_cloudwatch_metric_alarm.lambda_throttles.arn
}

output "api_gateway_5xx_alarm_name" {
  description = "API Gateway 5xx alarm name."
  value       = aws_cloudwatch_metric_alarm.api_gateway_5xx.alarm_name
}

output "api_gateway_5xx_alarm_arn" {
  description = "API Gateway 5xx alarm ARN."
  value       = aws_cloudwatch_metric_alarm.api_gateway_5xx.arn
}

output "scheduler_target_errors_alarm_name" {
  description = "Reminder scheduler target errors alarm name."
  value       = try(aws_cloudwatch_metric_alarm.scheduler_target_errors[0].alarm_name, null)
}

output "scheduler_target_errors_alarm_arn" {
  description = "Reminder scheduler target errors alarm ARN."
  value       = try(aws_cloudwatch_metric_alarm.scheduler_target_errors[0].arn, null)
}

output "notification_email_delivery_failures_alarm_name" {
  description = "Notification email delivery failures alarm name."
  value       = try(aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].alarm_name, null)
}

output "notification_email_delivery_failures_alarm_arn" {
  description = "Notification email delivery failures alarm ARN."
  value       = try(aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].arn, null)
}

output "notification_email_delivery_retry_exhausted_alarm_name" {
  description = "Notification email delivery retry exhausted alarm name."
  value       = try(aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].alarm_name, null)
}

output "notification_email_delivery_retry_exhausted_alarm_arn" {
  description = "Notification email delivery retry exhausted alarm ARN."
  value       = try(aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].arn, null)
}

output "notification_email_delivery_send_volume_high_alarm_name" {
  description = "Notification email delivery send volume high alarm name."
  value       = try(aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].alarm_name, null)
}

output "notification_email_delivery_send_volume_high_alarm_arn" {
  description = "Notification email delivery send volume high alarm ARN."
  value       = try(aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].arn, null)
}
