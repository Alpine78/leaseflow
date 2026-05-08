mock_provider "aws" {}

variables {
  name_prefix = "leaseflow-dev"
  aws_region  = "eu-north-1"
  environment = "dev"
  tags = {
    Project = "leaseflow"
  }
}

run "creates_safe_aggregate_delivery_dashboard" {
  command = plan

  assert {
    condition     = aws_cloudwatch_dashboard.notification_email_delivery.dashboard_name == "leaseflow-dev-notification-email-delivery"
    error_message = "Notification email delivery dashboard should use the expected name."
  }

  assert {
    condition     = output.dashboard_name == "leaseflow-dev-notification-email-delivery"
    error_message = "Dashboard name output should expose the safe dashboard name."
  }

  assert {
    condition     = strcontains(aws_cloudwatch_dashboard.notification_email_delivery.dashboard_body, "LeaseFlow/NotificationEmailDelivery")
    error_message = "Dashboard should use the notification email delivery namespace."
  }

  assert {
    condition     = strcontains(aws_cloudwatch_dashboard.notification_email_delivery.dashboard_body, "eu-north-1")
    error_message = "Dashboard should use the configured AWS region for metric widgets."
  }

  assert {
    condition = alltrue([
      for metric_name in [
        "candidate_count",
        "created_delivery_count",
        "attempted_count",
        "sent_count",
        "skipped_count",
        "failed_count",
        "retry_exhausted_count",
        "bounce_count",
        "complaint_count",
        "suppressed_contact_count"
      ] :
      strcontains(aws_cloudwatch_dashboard.notification_email_delivery.dashboard_body, metric_name)
    ])
    error_message = "Dashboard should include current and future aggregate delivery metric names."
  }

  assert {
    condition = alltrue([
      for dimension_value in [
        "environment",
        "dev",
        "service",
        "backend",
        "operation",
        "deliver_notification_emails",
        "result",
        "completed",
        "completed_with_failures",
        "disabled"
      ] :
      strcontains(aws_cloudwatch_dashboard.notification_email_delivery.dashboard_body, dimension_value)
    ])
    error_message = "Dashboard should use the expected low-cardinality delivery dimensions."
  }

  assert {
    condition = alltrue([
      for forbidden_value in [
        "tenant_id",
        "recipient_email",
        "contact_id",
        "notification_id",
        "request_id",
        "message_body",
        "credential",
        "ssm",
        "db_endpoint",
        "provider_payload"
      ] :
      !strcontains(lower(aws_cloudwatch_dashboard.notification_email_delivery.dashboard_body), forbidden_value)
    ])
    error_message = "Dashboard body must not include sensitive or high-cardinality fields."
  }
}
