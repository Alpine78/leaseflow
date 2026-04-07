mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_region" {
    defaults = {
      region = "eu-north-1"
    }
  }
}

variables {
  name_prefix          = "leaseflow-dev"
  lambda_function_name = "leaseflow-dev-backend"
  lambda_function_arn  = "arn:aws:lambda:eu-north-1:123456789012:function:leaseflow-dev-backend"
  schedule_expression  = "cron(0 5 * * ? *)"
  schedule_timezone    = "UTC"
  scan_window_days     = 7
  enabled              = true
  tags = {
    Project = "leaseflow"
  }
}

run "creates_daily_scheduler_resources" {
  command = plan

  assert {
    condition     = aws_scheduler_schedule.this.name == "leaseflow-dev-daily-reminder-scan"
    error_message = "Scheduler name should use the expected daily reminder naming."
  }

  assert {
    condition     = aws_scheduler_schedule.this.schedule_expression == "cron(0 5 * * ? *)"
    error_message = "Scheduler should use the configured schedule expression."
  }

  assert {
    condition     = aws_scheduler_schedule.this.state == "ENABLED"
    error_message = "Scheduler should be enabled by default."
  }

  assert {
    condition     = jsondecode(aws_scheduler_schedule.this.target[0].input)["detail-type"] == "scan_due_lease_reminders"
    error_message = "Scheduler input should trigger the internal reminder scan event."
  }

  assert {
    condition     = jsondecode(aws_scheduler_schedule.this.target[0].input).detail.days == 7
    error_message = "Scheduler input should include the configured reminder window."
  }

  assert {
    condition     = jsondecode(aws_iam_role.this.assume_role_policy).Statement[0].Principal.Service == "scheduler.amazonaws.com"
    error_message = "Scheduler role trust policy should allow EventBridge Scheduler."
  }

  assert {
    condition     = jsondecode(aws_iam_role_policy.this.policy).Statement[0].Action[0] == "lambda:InvokeFunction"
    error_message = "Scheduler role policy should allow Lambda invocation."
  }
}

run "supports_disabled_state" {
  command = plan

  variables {
    enabled = false
  }

  assert {
    condition     = aws_scheduler_schedule.this.state == "DISABLED"
    error_message = "Scheduler should support disabled state for controlled rollout."
  }
}
