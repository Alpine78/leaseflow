resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.name_prefix}-backend-errors"
  alarm_description   = "Baseline alarm for backend Lambda errors."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 1
  period              = 60
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.name_prefix}-backend-throttles"
  alarm_description   = "Baseline alarm for backend Lambda throttles."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  period              = 60
  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  alarm_name          = "${var.name_prefix}-http-api-5xx"
  alarm_description   = "Baseline alarm for HTTP API 5xx responses."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 1
  period              = 60
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    ApiId = var.api_id
    Stage = var.api_stage_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "scheduler_target_errors" {
  count = var.scheduler_enabled ? 1 : 0

  alarm_name          = "${var.name_prefix}-reminder-scheduler-target-errors"
  alarm_description   = "Baseline alarm for reminder scheduler target delivery failures."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  period              = 300
  namespace           = "AWS/Scheduler"
  metric_name         = "TargetErrorCount"
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    ScheduleGroup = var.scheduler_group_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "notification_email_delivery_failures" {
  count = var.notification_email_delivery_alarms_enabled ? 1 : 0

  alarm_name          = "${var.name_prefix}-notification-email-delivery-failures"
  alarm_description   = "Alarm for internal notification email delivery failures."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  period              = 300
  namespace           = "LeaseFlow/NotificationEmailDelivery"
  metric_name         = "failed_count"
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    environment = var.environment
    service     = "backend"
    operation   = "deliver_notification_emails"
    result      = "completed_with_failures"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "notification_email_delivery_retry_exhausted" {
  count = var.notification_email_delivery_alarms_enabled ? 1 : 0

  alarm_name          = "${var.name_prefix}-notification-email-delivery-retry-exhausted"
  alarm_description   = "Alarm for internal notification email deliveries that exhaust retry attempts."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  period              = 300
  namespace           = "LeaseFlow/NotificationEmailDelivery"
  metric_name         = "retry_exhausted_count"
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    environment = var.environment
    service     = "backend"
    operation   = "deliver_notification_emails"
    result      = "completed_with_failures"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "notification_email_delivery_send_volume_high" {
  count = var.notification_email_delivery_alarms_enabled ? 1 : 0

  alarm_name          = "${var.name_prefix}-notification-email-delivery-send-volume-high"
  alarm_description   = "Alarm for unexpectedly high internal notification email delivery attempts."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = var.notification_email_delivery_attempted_count_alarm_threshold
  period              = 3600
  namespace           = "LeaseFlow/NotificationEmailDelivery"
  metric_name         = "attempted_count"
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns

  dimensions = {
    environment = var.environment
    service     = "backend"
    operation   = "deliver_notification_emails"
    result      = "completed"
  }

  tags = var.tags
}
