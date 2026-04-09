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
