mock_provider "aws" {}

variables {
  name_prefix          = "leaseflow-dev"
  lambda_function_name = "leaseflow-dev-backend"
  api_id               = "api123456"
  api_stage_name       = "dev"
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
