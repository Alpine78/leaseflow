mock_provider "aws" {
  mock_resource "aws_cloudwatch_event_rule" {
    defaults = {
      arn = "arn:aws:events:eu-north-1:123456789012:rule/leaseflow-dev-ses-feedback"
    }
  }
}

variables {
  name_prefix          = "leaseflow-dev"
  lambda_function_name = "leaseflow-dev-backend"
  lambda_function_arn  = "arn:aws:lambda:eu-north-1:123456789012:function:leaseflow-dev-backend"
  enabled              = false
  tags = {
    Project = "leaseflow"
  }
}

run "defaults_create_no_eventbridge_processor_resources" {
  command = plan

  assert {
    condition     = length(aws_cloudwatch_event_rule.ses_feedback) == 0
    error_message = "SES feedback EventBridge rule should not be created by default."
  }

  assert {
    condition     = length(aws_cloudwatch_event_target.lambda) == 0
    error_message = "SES feedback Lambda target should not be created by default."
  }

  assert {
    condition     = length(aws_lambda_permission.eventbridge) == 0
    error_message = "SES feedback Lambda permission should not be created by default."
  }
}

run "enabled_rule_routes_ses_bounce_and_complaint_events_to_lambda" {
  command = apply

  variables {
    enabled = true
  }

  assert {
    condition     = length(aws_cloudwatch_event_rule.ses_feedback) == 1
    error_message = "SES feedback EventBridge rule should be created when enabled."
  }

  assert {
    condition     = jsondecode(aws_cloudwatch_event_rule.ses_feedback[0].event_pattern).source == ["aws.ses"]
    error_message = "SES feedback rule should match only SES events."
  }

  assert {
    condition     = jsonencode(sort(jsondecode(aws_cloudwatch_event_rule.ses_feedback[0].event_pattern)["detail-type"])) == jsonencode(["Email Bounced", "Email Complaint Received"])
    error_message = "SES feedback rule should match only bounce and complaint detail types."
  }

  assert {
    condition     = aws_cloudwatch_event_target.lambda[0].arn == var.lambda_function_arn
    error_message = "SES feedback rule target should invoke the backend Lambda ARN."
  }

  assert {
    condition     = aws_lambda_permission.eventbridge[0].principal == "events.amazonaws.com"
    error_message = "SES feedback Lambda permission should allow EventBridge service principal."
  }

  assert {
    condition     = aws_lambda_permission.eventbridge[0].function_name == var.lambda_function_name
    error_message = "SES feedback Lambda permission should target the configured Lambda function name."
  }

  assert {
    condition     = aws_lambda_permission.eventbridge[0].source_arn == aws_cloudwatch_event_rule.ses_feedback[0].arn
    error_message = "SES feedback Lambda permission should be scoped to the EventBridge rule ARN."
  }
}
