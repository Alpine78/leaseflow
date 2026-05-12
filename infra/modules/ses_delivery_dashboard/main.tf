locals {
  namespace = "LeaseFlow/NotificationEmailDelivery"

  completed_dimensions = [
    "environment", var.environment,
    "service", "backend",
    "operation", "deliver_notification_emails",
    "result", "completed",
  ]

  failed_dimensions = [
    "environment", var.environment,
    "service", "backend",
    "operation", "deliver_notification_emails",
    "result", "completed_with_failures",
  ]

  disabled_dimensions = [
    "environment", var.environment,
    "service", "backend",
    "operation", "deliver_notification_emails",
    "result", "disabled",
  ]

  feedback_processed_dimensions = [
    "environment", var.environment,
    "service", "backend",
    "operation", "process_ses_provider_feedback",
    "result", "processed",
  ]
}

resource "aws_cloudwatch_dashboard" "notification_email_delivery" {
  dashboard_name = "${var.name_prefix}-notification-email-delivery"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# Notification email delivery health\nAggregate LeaseFlow delivery metrics. Widgets can show no data until delivery is enabled and the worker emits metrics."
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 12
        height = 6
        properties = {
          title   = "Delivery run volume"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          stat    = "Sum"
          period  = 300
          metrics = [
            concat([local.namespace, "candidate_count"], local.completed_dimensions, [{ label = "candidates" }]),
            concat([local.namespace, "created_delivery_count"], local.completed_dimensions, [{ label = "created deliveries" }]),
            concat([local.namespace, "attempted_count"], local.completed_dimensions, [{ label = "attempted" }]),
            concat([local.namespace, "sent_count"], local.completed_dimensions, [{ label = "sent" }]),
            concat([local.namespace, "skipped_count"], local.completed_dimensions, [{ label = "skipped" }]),
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 2
        width  = 12
        height = 6
        properties = {
          title   = "Failure health"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          stat    = "Sum"
          period  = 300
          metrics = [
            concat([local.namespace, "failed_count"], local.failed_dimensions, [{ label = "failed" }]),
            concat([local.namespace, "retry_exhausted_count"], local.failed_dimensions, [{ label = "retry exhausted" }]),
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6
        properties = {
          title   = "Worker result categories"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          stat    = "SampleCount"
          period  = 300
          metrics = [
            concat([local.namespace, "attempted_count"], local.completed_dimensions, [{ label = "completed runs" }]),
            concat([local.namespace, "failed_count"], local.failed_dimensions, [{ label = "completed with failures" }]),
            concat([local.namespace, "attempted_count"], local.disabled_dimensions, [{ label = "disabled runs" }]),
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6
        properties = {
          title   = "Future feedback and suppression metrics"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          stat    = "Sum"
          period  = 300
          metrics = [
            concat([local.namespace, "bounce_count"], local.feedback_processed_dimensions, [{ label = "bounces" }]),
            concat([local.namespace, "complaint_count"], local.feedback_processed_dimensions, [{ label = "complaints" }]),
            concat([local.namespace, "suppressed_contact_count"], local.feedback_processed_dimensions, [{ label = "suppressed contacts" }]),
          ]
        }
      },
    ]
  })
}
