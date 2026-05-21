mock_provider "aws" {}
mock_provider "random" {}
mock_provider "archive" {}

variables {
  name_prefix         = "leaseflow-test"
  user_pool_id        = "eu-north-1_abc123"
  user_pool_client_id = "client123"
  api_url             = "https://abc123.execute-api.eu-north-1.amazonaws.com/dev"
  environment         = "dev"
  alarm_action_arns   = ["arn:aws:sns:eu-north-1:123456789012:leaseflow-test-alarms"]
}

run "defaults_alarm_posture" {
  command = plan

  assert {
    condition     = aws_cloudwatch_metric_alarm.synthetic_hc_failure.treat_missing_data == "breaching"
    error_message = "Alarm must treat missing data as breaching to detect scheduler failures."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.synthetic_hc_failure.evaluation_periods == 2
    error_message = "Alarm should require 2 consecutive failing periods before firing."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.synthetic_hc_failure.datapoints_to_alarm == 2
    error_message = "Alarm should require 2 failing datapoints before firing."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.synthetic_hc_failure.comparison_operator == "LessThanThreshold"
    error_message = "Alarm should fire when HealthCheckSuccess drops below threshold."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.synthetic_hc_failure.period == 900
    error_message = "Alarm period should match the 15-minute schedule (900 s)."
  }
}

run "defaults_scheduler_enabled" {
  command = plan

  assert {
    condition     = aws_scheduler_schedule.synthetic_hc.state == "ENABLED"
    error_message = "Scheduler must be ENABLED by default."
  }
}

run "disabled_scheduler" {
  command = plan

  variables {
    schedule_enabled = false
  }

  assert {
    condition     = aws_scheduler_schedule.synthetic_hc.state == "DISABLED"
    error_message = "Scheduler must be DISABLED when schedule_enabled = false."
  }
}

run "synthetic_user_no_welcome_email" {
  command = plan

  assert {
    condition     = aws_cognito_user.synthetic.message_action == "SUPPRESS"
    error_message = "Synthetic user creation must suppress the welcome email."
  }
}

run "lambda_timeout_sufficient" {
  command = plan

  assert {
    condition     = aws_lambda_function.synthetic_hc.timeout == 30
    error_message = "Lambda timeout must be at least 30 s to allow two HTTP calls plus auth."
  }
}
