output "dashboard_name" {
  description = "Notification email delivery dashboard name."
  value       = aws_cloudwatch_dashboard.notification_email_delivery.dashboard_name
}
