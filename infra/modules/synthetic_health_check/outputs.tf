output "lambda_function_arn" {
  value       = aws_lambda_function.synthetic_hc.arn
  description = "Synthetic health check Lambda function ARN."
}

output "lambda_function_name" {
  value       = aws_lambda_function.synthetic_hc.function_name
  description = "Synthetic health check Lambda function name."
}

output "alarm_name" {
  value       = aws_cloudwatch_metric_alarm.synthetic_hc_failure.alarm_name
  description = "CloudWatch alarm name for synthetic health check failures."
}
