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

  dimensions = {
    ScheduleGroup = var.scheduler_group_name
  }

  tags = var.tags
}
