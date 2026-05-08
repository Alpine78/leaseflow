mock_provider "aws" {}

variables {
  name_prefix          = "leaseflow-dev"
  lambda_function_name = "leaseflow-dev-backend"
  api_id               = "api123456"
  api_stage_name       = "dev"
  environment          = "dev"
  scheduler_group_name = "default"
  scheduler_enabled    = true
  tags = {
    Project = "leaseflow"
  }
}

run "creates_baseline_alarm_resources" {
  command = plan

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_errors.alarm_name == "leaseflow-dev-backend-errors"
    error_message = "Lambda errors alarm should use the expected name."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_errors.namespace == "AWS/Lambda"
    error_message = "Lambda errors alarm should use the AWS/Lambda namespace."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_errors.metric_name == "Errors"
    error_message = "Lambda errors alarm should track Lambda Errors."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_errors.dimensions.FunctionName == "leaseflow-dev-backend"
    error_message = "Lambda errors alarm should scope to the backend function."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_errors.evaluation_periods == 2
    error_message = "Lambda errors alarm should use balanced two-period evaluation."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_errors.datapoints_to_alarm == 2
    error_message = "Lambda errors alarm should require two breaching datapoints."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_errors.treat_missing_data == "notBreaching"
    error_message = "Lambda errors alarm should ignore missing datapoints."
  }

  assert {
    condition     = length(coalesce(aws_cloudwatch_metric_alarm.lambda_errors.alarm_actions, [])) == 0
    error_message = "Lambda errors alarm should have no actions by default."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_throttles.metric_name == "Throttles"
    error_message = "Lambda throttles alarm should track Lambda Throttles."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.lambda_throttles.evaluation_periods == 1
    error_message = "Lambda throttles alarm should trigger on a single period."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.api_gateway_5xx.namespace == "AWS/ApiGateway"
    error_message = "API 5xx alarm should use the API Gateway namespace."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.api_gateway_5xx.metric_name == "5xx"
    error_message = "API alarm should track HTTP API 5xx responses."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.api_gateway_5xx.dimensions.ApiId == "api123456"
    error_message = "API alarm should scope to the HTTP API ID."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.api_gateway_5xx.dimensions.Stage == "dev"
    error_message = "API alarm should scope to the deployment stage."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.scheduler_target_errors[0].namespace == "AWS/Scheduler"
    error_message = "Scheduler alarm should use the AWS/Scheduler namespace."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.scheduler_target_errors[0].metric_name == "TargetErrorCount"
    error_message = "Scheduler alarm should track target delivery failures."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.scheduler_target_errors[0].dimensions.ScheduleGroup == "default"
    error_message = "Scheduler alarm should scope to the configured schedule group."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.scheduler_target_errors[0].period == 300
    error_message = "Scheduler alarm should use a 5-minute period."
  }

  assert {
    condition     = length(aws_cloudwatch_metric_alarm.notification_email_delivery_failures) == 1
    error_message = "Notification email delivery failures alarm should be created by default."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].alarm_name == "leaseflow-dev-notification-email-delivery-failures"
    error_message = "Notification email delivery failures alarm should use the expected name."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].namespace == "LeaseFlow/NotificationEmailDelivery"
    error_message = "Notification email delivery failures alarm should use the delivery namespace."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].metric_name == "failed_count"
    error_message = "Notification email delivery failures alarm should track failed_count."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].dimensions.environment == "dev"
    error_message = "Notification email delivery failures alarm should scope to the environment dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].dimensions.service == "backend"
    error_message = "Notification email delivery failures alarm should scope to the backend service dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].dimensions.operation == "deliver_notification_emails"
    error_message = "Notification email delivery failures alarm should scope to the delivery operation dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].dimensions.result == "completed_with_failures"
    error_message = "Notification email delivery failures alarm should scope to failed delivery runs."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].comparison_operator == "GreaterThanOrEqualToThreshold"
    error_message = "Notification email delivery failures alarm should trigger at or above the threshold."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].threshold == 1
    error_message = "Notification email delivery failures alarm should trigger on one failed delivery."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].period == 300
    error_message = "Notification email delivery failures alarm should use a five-minute period."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].evaluation_periods == 1
    error_message = "Notification email delivery failures alarm should evaluate one period."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].datapoints_to_alarm == 1
    error_message = "Notification email delivery failures alarm should require one breaching datapoint."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].statistic == "Sum"
    error_message = "Notification email delivery failures alarm should sum metric values."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].treat_missing_data == "notBreaching"
    error_message = "Notification email delivery failures alarm should treat missing data as not breaching."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].alarm_name == "leaseflow-dev-notification-email-delivery-retry-exhausted"
    error_message = "Notification email delivery retry exhausted alarm should use the expected name."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].namespace == "LeaseFlow/NotificationEmailDelivery"
    error_message = "Notification email delivery retry exhausted alarm should use the delivery namespace."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].metric_name == "retry_exhausted_count"
    error_message = "Notification email delivery retry exhausted alarm should track retry_exhausted_count."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].dimensions.environment == "dev"
    error_message = "Notification email delivery retry exhausted alarm should scope to the environment dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].dimensions.service == "backend"
    error_message = "Notification email delivery retry exhausted alarm should scope to the backend service dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].dimensions.operation == "deliver_notification_emails"
    error_message = "Notification email delivery retry exhausted alarm should scope to the delivery operation dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].dimensions.result == "completed_with_failures"
    error_message = "Notification email delivery retry exhausted alarm should scope to failed delivery runs."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].comparison_operator == "GreaterThanOrEqualToThreshold"
    error_message = "Notification email delivery retry exhausted alarm should trigger at or above the threshold."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].threshold == 1
    error_message = "Notification email delivery retry exhausted alarm should trigger on one exhausted retry."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].period == 300
    error_message = "Notification email delivery retry exhausted alarm should use a five-minute period."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].evaluation_periods == 1
    error_message = "Notification email delivery retry exhausted alarm should evaluate one period."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].datapoints_to_alarm == 1
    error_message = "Notification email delivery retry exhausted alarm should require one breaching datapoint."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].statistic == "Sum"
    error_message = "Notification email delivery retry exhausted alarm should sum metric values."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].treat_missing_data == "notBreaching"
    error_message = "Notification email delivery retry exhausted alarm should treat missing data as not breaching."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].alarm_name == "leaseflow-dev-notification-email-delivery-send-volume-high"
    error_message = "Notification email delivery send volume alarm should use the expected name."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].namespace == "LeaseFlow/NotificationEmailDelivery"
    error_message = "Notification email delivery send volume alarm should use the delivery namespace."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].metric_name == "attempted_count"
    error_message = "Notification email delivery send volume alarm should track attempted_count."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].dimensions.environment == "dev"
    error_message = "Notification email delivery send volume alarm should scope to the environment dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].dimensions.service == "backend"
    error_message = "Notification email delivery send volume alarm should scope to the backend service dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].dimensions.operation == "deliver_notification_emails"
    error_message = "Notification email delivery send volume alarm should scope to the delivery operation dimension."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].dimensions.result == "completed"
    error_message = "Notification email delivery send volume alarm should scope to completed delivery runs."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].comparison_operator == "GreaterThanThreshold"
    error_message = "Notification email delivery send volume alarm should trigger above the threshold."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].threshold == 100
    error_message = "Notification email delivery send volume alarm should use the default threshold."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].period == 3600
    error_message = "Notification email delivery send volume alarm should use a one-hour period."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].evaluation_periods == 1
    error_message = "Notification email delivery send volume alarm should evaluate one period."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].datapoints_to_alarm == 1
    error_message = "Notification email delivery send volume alarm should require one breaching datapoint."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].statistic == "Sum"
    error_message = "Notification email delivery send volume alarm should sum metric values."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].treat_missing_data == "notBreaching"
    error_message = "Notification email delivery send volume alarm should treat missing data as not breaching."
  }
}

run "attaches_alarm_actions_when_supplied" {
  command = plan

  variables {
    alarm_action_arns = [
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    ]
  }

  assert {
    condition = length(aws_cloudwatch_metric_alarm.lambda_errors.alarm_actions) == 1 && contains(
      aws_cloudwatch_metric_alarm.lambda_errors.alarm_actions,
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    )
    error_message = "Lambda errors alarm should publish to the supplied action ARN."
  }

  assert {
    condition = length(aws_cloudwatch_metric_alarm.lambda_throttles.alarm_actions) == 1 && contains(
      aws_cloudwatch_metric_alarm.lambda_throttles.alarm_actions,
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    )
    error_message = "Lambda throttles alarm should publish to the supplied action ARN."
  }

  assert {
    condition = length(aws_cloudwatch_metric_alarm.api_gateway_5xx.alarm_actions) == 1 && contains(
      aws_cloudwatch_metric_alarm.api_gateway_5xx.alarm_actions,
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    )
    error_message = "API 5xx alarm should publish to the supplied action ARN."
  }

  assert {
    condition = length(aws_cloudwatch_metric_alarm.scheduler_target_errors[0].alarm_actions) == 1 && contains(
      aws_cloudwatch_metric_alarm.scheduler_target_errors[0].alarm_actions,
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    )
    error_message = "Scheduler target errors alarm should publish to the supplied action ARN."
  }

  assert {
    condition = length(aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].alarm_actions) == 1 && contains(
      aws_cloudwatch_metric_alarm.notification_email_delivery_failures[0].alarm_actions,
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    )
    error_message = "Notification email delivery failures alarm should publish to the supplied action ARN."
  }

  assert {
    condition = length(aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].alarm_actions) == 1 && contains(
      aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted[0].alarm_actions,
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    )
    error_message = "Notification email delivery retry exhausted alarm should publish to the supplied action ARN."
  }

  assert {
    condition = length(aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].alarm_actions) == 1 && contains(
      aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].alarm_actions,
      "arn:aws:sns:eu-north-1:123456789012:leaseflow-dev-baseline-alarm-notifications"
    )
    error_message = "Notification email delivery send volume alarm should publish to the supplied action ARN."
  }
}

run "omits_scheduler_alarm_when_disabled" {
  command = plan

  variables {
    scheduler_enabled = false
  }

  assert {
    condition     = length(aws_cloudwatch_metric_alarm.scheduler_target_errors) == 0
    error_message = "Scheduler alarm should be omitted when the scheduler is disabled."
  }
}

run "omits_notification_email_delivery_alarms_when_disabled" {
  command = plan

  variables {
    notification_email_delivery_alarms_enabled = false
  }

  assert {
    condition     = length(aws_cloudwatch_metric_alarm.notification_email_delivery_failures) == 0
    error_message = "Notification email delivery failures alarm should be omitted when disabled."
  }

  assert {
    condition     = length(aws_cloudwatch_metric_alarm.notification_email_delivery_retry_exhausted) == 0
    error_message = "Notification email delivery retry exhausted alarm should be omitted when disabled."
  }

  assert {
    condition     = length(aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high) == 0
    error_message = "Notification email delivery send volume alarm should be omitted when disabled."
  }
}

run "uses_configured_notification_email_delivery_attempt_threshold" {
  command = plan

  variables {
    notification_email_delivery_attempted_count_alarm_threshold = 25
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.notification_email_delivery_send_volume_high[0].threshold == 25
    error_message = "Notification email delivery send volume alarm should use the configured threshold."
  }
}
