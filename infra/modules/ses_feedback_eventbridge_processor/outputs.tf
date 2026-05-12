output "rule_name" {
  value       = try(aws_cloudwatch_event_rule.ses_feedback[0].name, null)
  description = "SES feedback EventBridge rule name when enabled."
}

output "enabled" {
  value       = length(aws_cloudwatch_event_rule.ses_feedback) > 0
  description = "Whether SES feedback EventBridge routing is configured."
}
